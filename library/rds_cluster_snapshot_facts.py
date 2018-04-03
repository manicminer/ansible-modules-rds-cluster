#!/usr/bin/python

DOCUMENTATION = '''
---
module: rds_cluster_snapshot_facts
short_description: Searches for RDS cluster snapshots to obtain the ID(s)
description:
    - Searches for RDS cluster snapshots to obtain the ID(s)
options:
  snapshot_id:
    description:
      - ID of the snapshot to search for
    required: false
  cluster_id:
    description:
      - ID of a DB cluster
    required: false
  max_records:
    description:
      - Maximum number of records returned [by AWS]
    required: false
  id_regex:
    description:
      - Filter the results by matching this regular expression against the snapshot ID.
    default: null
    required: false
  snapshot_type:
    description:
      - Filter the results by snapshot type.
    choices: ['automated', 'manual', 'shared', 'public']
    default: null
    required: false
  status:
    description:
      - Filter the results by snapshot status.
    choices:
      - available
      - backing-up
      - creating
      - deleted
      - deleting
      - failed
      - modifying
      - rebooting
      - resetting-master-credentials
    default: null
    required: false
  sort:
    description:
      - Optional attribute which with to sort the results.
    choices: ['id', 'snapshot_create_time', 'cluster_create_time']
    default: null
    required: false
  sort_order:
    description:
      - Order in which to sort results.
      - Only used when the 'sort' parameter is specified.
    choices: ['ascending', 'descending']
    default: 'ascending'
    required: false
  sort_start:
    description:
      - Which result to start with (when sorting).
      - Corresponds to Python slice notation.
    default: null
    required: false
  sort_end:
    description:
      - Which result to end with (when sorting).
      - Corresponds to Python slice notation.
    default: null
    required: false

author: "Tom Bamford (@manicminer)"
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Basic Snapshot Search
- local_action:
    module: rds_cluster_snapshot_facts
    snapshot_id: my-local-snapshot

# Find all
- local_action:
    module: rds_cluster_snapshot_facts

# Find latest, available, automated snapshot
- local_action:
    module: rds_cluster_snapshot_facts
    cluster_id: my-rds-cluster
    snapshot_type: automated
    status: available
    sort: snapshot_create_time
    sort_order: descending
    sort_end: 1
'''

try:
    import boto3
    import botocore.exceptions
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


def find_snapshot_facts(module, client, snapshot_id=None, cluster_id=None, max_records=None, id_regex=None, snapshot_type=None, status=None, sort=None, sort_order=None, sort_start=None, sort_end=None):

    api_args = dict()
    if snapshot_id:
        api_args['DBClusterSnapshotIdentifier'] = snapshot_id
    if cluster_id:
        api_args['DBClusterIdentifier'] = cluster_id
    if snapshot_type:
        api_args['SnapshotType'] = snapshot_type
    if max_records:
        api_args['MaxRecords'] = max_records

    try:
        snapshots = client.describe_db_cluster_snapshots(**api_args)
    except (botocore.exceptions.ClientError, boto.exception.BotoServerError), e:
        module.fail_json(msg=str(e), api_args=api_args)

    results = []

    if 'DBClusterSnapshots' in snapshots:
        if id_regex:
            regex = re.compile(id_regex)

        for snapshot in snapshots['DBClusterSnapshots']:

            data = {
                'availability_zones': snapshot['AvailabilityZones'],
                'snapshot_id': snapshot['DBClusterSnapshotIdentifier'],
                'cluster_id': snapshot['DBClusterIdentifier'],
                'snapshot_create_time': snapshot['SnapshotCreateTime'],
                'engine': snapshot['Engine'],
                'allocated_storage': snapshot['AllocatedStorage'],
                'status': snapshot['Status'],
                'port': snapshot['Port'],
                'vpc_id': snapshot['VpcId'],
                'cluster_create_time': snapshot['ClusterCreateTime'],
                'master_username': snapshot['MasterUsername'],
                'engine_version': snapshot['EngineVersion'],
                'license_model': snapshot['LicenseModel'],
                'snapshot_type': snapshot['SnapshotType'],
                'percent_progress': snapshot['PercentProgress'],
                'storage_encrypted': snapshot['StorageEncrypted'],
                'db_cluster_snapshot_arn': snapshot['DBClusterSnapshotArn'],
                'iam_database_authentication_enabled': snapshot['IAMDatabaseAuthenticationEnabled'],
            }
            if 'KmsKeyId' in snapshot:
                data['kms_key_id'] = snapshot['KmsKeyId']
            if 'SourceDBClusterSnapshotArn' in snapshot:
                data['source_db_cluster_snapshot_arn'] = snapshot['SourceDBClusterSnapshotArn']

            if id_regex:
                if not regex.match(data['snapshot_id']):
                    continue

            if snapshot_type:
                if data['snapshot_type'] != snapshot_type:
                    continue

            if status:
                if data['status'] != status:
                    continue

            results.append(data)

    if sort:
        results.sort(key=lambda e: e[sort], reverse=(sort_order=='descending'))

    try:
        if sort and sort_start and sort_end:
            results = results[int(sort_start):int(sort_end)]
        elif sort and sort_start:
            results = results[int(sort_start):]
        elif sort and sort_end:
            results = results[:int(sort_end)]
    except TypeError:
        module.fail_json(msg="Please supply numeric values for sort_start and/or sort_end")

    module.exit_json(results=results)


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            snapshot_id=dict(),
            cluster_id=dict(),
            max_records=dict(),
            id_regex=dict(required=False, default=None),
            snapshot_type=dict(required=False, default=None,
                choices=['automated', 'manual', 'shared', 'public']),
            status = dict(required=False, default=None,
                choices=['available', 'backing-up', 'creating', 'deleted',
                         'deleting', 'failed', 'modifying', 'rebooting',
                         'resetting-master-credentials']),
            sort = dict(required=False, default=None,
                choices=['id', 'snapshot_create_time']),
            sort_order = dict(required=False, default='ascending',
                choices=['ascending', 'descending']),
            sort_start = dict(required=False),
            sort_end = dict(required=False),
        )
    )
    module = AnsibleModule(argument_spec=argument_spec, mutually_exclusive=['snapshot_id', 'cluster_id'])

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 required for this module')

    snapshot_id = module.params.get('snapshot_id')
    cluster_id = module.params.get('cluster_id')
    max_records = module.params.get('max_records')
    id_regex = module.params.get('id_regex')
    snapshot_type = module.params.get('snapshot_type')
    status = module.params.get('status')
    sort = module.params.get('sort')
    sort_order = module.params.get('sort_order')
    sort_start = module.params.get('sort_start')
    sort_end = module.params.get('sort_end')

    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        rds = boto3_conn(module, conn_type='client', resource='rds', region=region, endpoint=ec2_url, **aws_connect_kwargs)
    except botocore.exceptions.ClientError, e:
        module.fail_json(msg="Boto3 Client Error - " + str(e))

    find_snapshot_facts(
        module=module,
        client=rds,
        snapshot_id=snapshot_id,
        cluster_id=cluster_id,
        max_records=max_records,
        id_regex=id_regex,
        snapshot_type=snapshot_type,
        status=status,
        sort=sort,
        sort_order=sort_order,
        sort_start=sort_start,
        sort_end=sort_end
    )

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
