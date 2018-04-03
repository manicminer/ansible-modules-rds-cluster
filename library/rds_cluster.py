#!/usr/bin/python

DOCUMENTATION = '''
---
module: rds_cluster
short_description: Manage RDS database clusters (currently Aurora)
description:
    - Manages RDS database clusters
    - Can additionally restore clusters from a snapshot
options:
  cluster_id:
    description:
      - ID for the new cluster
    required: true
  snapshot_arn:
    description:
      - ARN of the snapshot to restore from.
      - If specified, and cluster does not exist, will restore from the specified snapshot.
      - When not specified, a new cluster will be created.
    required: false
  availability_zones:
    description:
      - List of availability zones in which to locate the new cluster
    default: none
  engine:
    description:
      - Database engine to use for the new cluster
      - Used when creating a new cluster or restoring from snapshot.
    choices:
      - aurora
    default: aurora
  engine_version:
    description:
      - Database engine version to create
      - Defaults to the same engine version as the source snapshot
    default: null
  master_username:
    description:
      - Master username to set.
      - Used when state=present and snapshot_arn is not set.
    default: null
  master_password:
    description:
      - Master password to set.
      - Used when state=present and snapshot_arn is not set.
    default: null
  port:
    description:
      - Port to listen on for the new cluster
      - Defaults to the same port as the source snapshot cluster
    default: null
  subnet_group:
    description:
      - Subnet group in which to create the new cluster.
      - Used when creating a new cluster or restoring from snapshot.
    required: true
  database_name:
    description:
      - Database name to create in the new cluster
      - Defaults to the same database as the source snapshot cluster
    default: null
  option_group:
    description:
      - Option group to use for the new cluster
    default: null
  state:
    description:
      - "present" to create a cluster (from a snapshot if specified), "absent" to delete a cluster
    choices:
      - present
      - absent
    default: present
    required: false
  tags:
    description:
      - Dictionary of tags to assign to the new cluster
    default: null
  vpc_security_group_ids:
    description:
      - List of VPC security group IDs with which to associate the new cluster
    default: null
  wait:
    description:
      - Whether or not to wait for the restored cluster to become available
    default: false
  wait_timeout:
    description:
      - Number of seconds to wait for the new cluster to become available before giving up
    default: 600 when creating, 3600 when restoring from snapshot (yes an entire hour)

author: "Tom Bamford (@manicminer)"
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Create a new cluster and don't wait for it to become available
- local_action:
    module: rds_cluster
    cluster_id: my-new-cluster
    subnet_group: my-subnet-group-name
    vpc_security_group_ids:
      - sg-123456
      - sg-567890
    tags:
      Name: my-new-cluster
      Env: staging
      Owner: my-name

# Restore from a snapshot and wait up to 20 mins for it to become available
- local_action:
    module: rds_cluster
    cluster_id: my-new-cluster
    snapshot_arn: "arn:aws:rds:us-east-1:1234567890:cluster-snapshot:rds:my-existing-snapshot"
    subnet_group: my-subnet-group-name
    vpc_security_group_ids:
      - sg-123456
      - sg-567890
    tags:
      Name: my-new-cluster
      Env: staging
      Owner: my-name
    wait: yes
'''

try:
    import boto3
    import botocore.exceptions
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


def create_cluster(module, client, **params):

    api_args = dict()
    if params['availability_zones'] is not None:
        api_args['AvailabilityZones'] = params['availability_zones']
    if params['engine_version'] is not None:
        api_args['EngineVersion'] = params['engine_version']
    if params['port'] is not None:
        api_args['Port'] = params['port']
    if params['database_name'] is not None:
        api_args['DatabaseName'] = params['database_name']
    if params['option_group'] is not None:
        api_args['OptionGroupName'] = params['option_group']
    if params['vpc_security_group_ids'] is not None:
        api_args['VpcSecurityGroupIds'] = params['vpc_security_group_ids']
    if params['tags'] is not None:
        api_args['Tags'] = [dict(Key=k, Value=v) for k, v in params['tags'].iteritems()]

    try:
        check_cluster = client.describe_db_clusters(DBClusterIdentifier=params['cluster_id'])

        if 'DBClusters' not in check_cluster or len(check_cluster['DBClusters']) != 1:
            module.fail_json(msg='Failed to retrieve details for existing cluster')

        # Determine cluster modifications to make
        cluster = check_cluster['DBClusters'][0]
        modify_args = dict()
        for opt, val in api_args.iteritems():
            if opt == 'VpcSecurityGroupIds':
                if sorted([g['VpcSecurityGroupId'] for g in cluster['VpcSecurityGroups']]) != sorted(val):
                    modify_args[opt] = val
            elif cluster[opt] != val:
                modify_args[opt] = val

        if modify_args:
            # Modify existing cluster
            result = client.modify_db_cluster(DBClusterIdentifier=params['cluster_id'], **modify_args)
        else:
            # Return existing cluster details verbatim
            result = dict(DBCluster=cluster)

        if params['wait_timeout'] == 0:
            params['wait_timeout'] = 600

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'DBClusterNotFoundFault':

            if params['cluster_id'] is not None:
                api_args['DBClusterIdentifier'] = params['cluster_id']
            if params['engine'] is not None:
                api_args['Engine'] = params['engine']
            if params['subnet_group'] is not None:
                api_args['DBSubnetGroupName'] = params['subnet_group']

            try:
                # Restore from snapshot
                if params['snapshot_arn'] is not None:
                    api_args['SnapshotIdentifier'] = params['snapshot_arn']
                    result = client.restore_db_cluster_from_snapshot(**api_args)
                    if params['wait_timeout'] == 0:
                        params['wait_timeout'] = 3600

                # Create new cluster
                else:
                    if params['master_username'] is not None:
                        api_args['MasterUsername'] = params['master_username']
                    if params['master_password'] is not None:
                        api_args['MasterUserPassword'] = params['master_password']
                    result = client.create_db_cluster(**api_args)
                    if params['wait_timeout'] == 0:
                        params['wait_timeout'] = 600

            except (botocore.exceptions.ClientError, boto.exception.BotoServerError) as e:
                module.fail_json(msg=str(e), api_args=api_args)
        else:
            module.fail_json(msg=str(e), api_args=api_args)

    if params['wait']:
        wait_timeout = time.time() + params['wait_timeout']
        ready = False
        while not ready and wait_timeout > time.time():
            try:
                check_cluster = client.describe_db_clusters(DBClusterIdentifier=params['cluster_id'])
                if 'DBClusters' in check_cluster and len(check_cluster['DBClusters']) == 1:
                    if check_cluster['DBClusters'][0]['Status'].lower() == 'available':
                        ready = True

            except (botocore.exceptions.ClientError, boto.exception.BotoServerError), e:
                pass

            if not ready:
                time.sleep(5)

        if wait_timeout <= time.time():
            if 'DBClusters' in check_cluster and len(check_cluster['DBClusters']) == 1:
                cluster = check_cluster['DBClusters'][0]
            else:
                cluster = None
            module.fail_json(msg='Timed out waiting for DB cluster to become available', cluster=cluster)

    module.exit_json(result=result)


def main():
    module_args = dict(
        availability_zones=dict(type='list', required=False),
        cluster_id=dict(required=True),
        database_name=dict(required=False),
        engine=dict(required=False, choices=['aurora'], default='aurora'),
        engine_version=dict(required=False),
        master_username=dict(required=False),
        master_password=dict(required=False, no_log=True),
        option_group=dict(required=False),
        port=dict(type='int', required=False),
        snapshot_arn=dict(required=False),
        state = dict(required=False, default='present', choices=['present', 'absent']),
        subnet_group=dict(required=True),
        tags=dict(type='dict', required=False),
        vpc_security_group_ids=dict(type='list', required=False),
        wait=dict(type='bool', required=False, default=False),
        wait_timeout=dict(type='int', required=False, default=0),
    )
    argument_spec = ec2_argument_spec()
    argument_spec.update(module_args)
    module = AnsibleModule(argument_spec=argument_spec)
    args_dict = {arg: module.params.get(arg) for arg in module_args.keys()}

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 required for this module')

    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        rds = boto3_conn(module, conn_type='client', resource='rds', region=region, endpoint=ec2_url, **aws_connect_kwargs)
    except botocore.exceptions.ClientError, e:
        module.fail_json(msg="Boto3 Client Error - " + str(e))

    if module.params.get('state') == 'present':
        create_cluster(module=module, client=rds, **args_dict)
    elif module.params.get('state') == 'absent':
        terminate_cluster(module, rds, **args_dict)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
