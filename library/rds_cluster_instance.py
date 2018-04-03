#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: rds_cluster_instance
short_description: Manages individual RDS Aurora clusterinstances
description:
    - Manages individual RDS Aurora cluster instances
options:
  apply_immediately:
    description:
      - Indicates whether changes to an existing instance should be applied immediately or during the next maintenance window.
      - Used when state=present and the instance already exists.
    choices: ["yes", "no"]
    required: false
    default: false
  auto_minor_version_upgrade:
    description:
      - Indicates that minor version upgrades should be applied automatically.
      - Used when state=present.
    choices: ["yes", "no"]
    required: false
    default: true
  availability_zone:
    description:
      - Availability zone in which to launch the instance.
      - Used when state=present.
      - When not specified, a random system-chosen AZ will be used.
    required: false
    default: null
  cloudwatch_logs_exports:
    description:
      - The list of log types that need to be enabled for exporting to CloudWatch Logs.
      - Used when state=present.
    required: false
    default: []
  cluster_id:
    description:
      - Identifier of a cluster the instance will belong to.
      - Used when state=present and instance does not exist.
    required: false
    default: null
  copy_tags_to_snapshot:
    description:
      - Whether or not to copy tag values to snapshots when they are created.
      - Used when state=present.
    choices:
        - yes
        - no
    required: false
    default: true
  engine:
    description:
      - Database engine to use (currently only supports, and default to, aurora)
      - Used when state=present and instance does not exist.
    choices:
        - aurora
    required: false
    default: aurora
  instance_id:
    description:
      - Identifier of a DB instance
    required: false
  instance_type:
    description:
      - The instance type of the database.
      - Required when state=present.
    required: false
    default: null
  monitoring_interval:
    description:
      - Interval in seconds between points when enhanced monitoring metrics are collected.
      - Omit or set to zero to disable enhanced monitoring
      - Used when state=present.
    choices: [0, 1, 5, 10, 15, 30, 60]
    required: false
    default: 0
  monitoring_role_arn:
    description:
      - ARN for the IAM role that permits RDS to send ehnanced monitoring metrics to CloudWatch Logs.
      - Required when monitoring_interval > 0
      - Used when state=present.
    required: false
    default: null
  multi_az:
    description:
      - Specifies if this is a Multi-availability-zone deployment.
      - Can not be used in conjunction with availability_zone parameter.
      - Used when state=present.
    choices:
        - yes
        - no
    required: false
    default: false
  option_group:
    description:
      - Name of the DB option group to associate with this instance.
      - Used when state=present.
      - If omitted then the RDS default option group will be used.
    required: false
    default: null
  parameter_group:
    description:
      - Name of the DB parameter group to associate with this instance.
      - Used when state=present.
      - If omitted then the RDS default parameter group will be used.
    required: false
    default: null
  performance_insights:
    description:
      - Whether ornot to enable Performance Insights for the DB instance.
      - Used when state=present.
    required: false
    default: null
  preferred_maintenance_window:
    description:
      - Maintenance window in format of ddd:hh24:mi-ddd:hh24:mi.  (Example: Mon:22:00-Mon:23:15)
      - Used when state=present.
      - If not specified then a random maintenance window is assigned.
    required: false
    default: null
  promotion_tier:
    description:
      - Order in which a replica instance is promoted to primary after failure of the primary instance.
      - Used when state=present.
      - If not specified for any replica instance, then RDS will promote the largest avaiable replica.
    required: false
    default: null
  publicly_accessible:
    description:
      - Whether the resource should be publicly accessible or not.
      - Used when state=present.
    required: false
    default: false
  state:
    description:
      - "present" to create an instance, "absent" to delete an instance
    choices:
      - present
      - absent
    default: present
    required: false
  subnet_group:
    description:
      - The DB subnet group in which to launch the instance.
      - Required when state=present and instance does not exist.
    required: false
    default: null
  tags:
    description:
      - Dictionary of tags to apply to a resource.
      - Used when state=present.
    required: false
    default: null
  wait:
    description:
      - Whether or not to wait for instance to become available.
      - Used when state=present.
    choices:
        - yes
        - no
    required: false
    default: false
  wait_timeout:
    description:
      - How long to wait for instance to become available, when wait=yes
      - Defaults to 20 minutes.
      - Used when state=present and wait=yes.
    required: false
    default: 1200

author: "Tom Bamford (@manicminer)"
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Basic instance creation
- local_action:
    module: rds_cluster_instance
    instance_id: my-new-instance
    instance_type: db.t2.small
    cluster_id: my-aurora-cluster
    subnet_group: my-db-subnet-group
    tags:
      Name: my-new-instance
    state: present
'''

try:
    import boto3
    import botocore.exceptions
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

import time


def create_db_instance(module, client, **params):

    api_args = dict()

    if params['instance_type'] is not None:
        api_args['DBInstanceClass'] = params['instance_type']
    if params['availability_zone'] is not None:
        api_args['AvailabilityZone'] = params['availability_zone']
    if params['preferred_maintenance_window'] is not None:
        api_args['PreferredMaintenanceWindow'] = params['preferred_maintenance_window']
    if params['parameter_group'] is not None:
        api_args['DBParameterGroupName'] = params['parameter_group']
    if params['multi_az'] is not None:
        api_args['MultiAZ'] = params['multi_az']
    if params['auto_minor_version_upgrade'] is not None:
        api_args['AutoMinorVersionUpgrade'] = params['auto_minor_version_upgrade']
    if params['option_group'] is not None:
        api_args['OptionGroupName'] = params['option_group']
    if params['publicly_accessible'] is not None:
        api_args['PubliclyAccessible'] = params['publicly_accessible']
    if params['copy_tags_to_snapshot'] is not None:
        api_args['CopyTagsToSnapshot'] = params['copy_tags_to_snapshot']
    if params['monitoring_interval'] is not None:
        api_args['MonitoringInterval'] = params['monitoring_interval']
    if params['monitoring_role_arn'] is not None:
        api_args['MonitoringRoleArn'] = params['monitoring_role_arn']
    if params['promotion_tier'] is not None:
        api_args['PromotionTier'] = params['promotion_tier']
    if params['performance_insights'] is not None:
        api_args['EnablePerformanceInsights'] = params['performance_insights']
    if params['cloudwatch_logs_exports'] is not None:
        api_args['EnableCloudwatchLogsExports'] = params['cloudwatch_logs_exports']

    tags = None
    if params['tags'] is not None:
        tags = [{'Key': k, 'Value': v} for k, v in params['tags'].iteritems()]

    try:
        check_instance = client.describe_db_instances(DBInstanceIdentifier=params['instance_id'])

        if 'DBInstances' not in check_instance or len(check_instance['DBInstances']) != 1:
            module.fail_json(msg='Failed to retrieve details for existing database instance')

        # Determine instance modifications to make
        instance = check_instance['DBInstances'][0]
        modify_args = dict()
        for opt, val in api_args.iteritems():
            if opt == 'DBParameterGroupName':
                if [g['DBParameterGroupName'] for g in instance['DBParameterGroups']] != [val,]:
                    modify_args[opt] = val
            elif opt == 'EnablePerformanceInsights':
                if instance['PerformanceInsightsEnabled'] != val:
                    modify_args[opt] = val
            elif opt not in instance or instance[opt] != val:
                modify_args[opt] = val

        if modify_args:
            # Modify existing instance
            result = client.modify_db_instance(DBInstanceIdentifier=params['instance_id'], ApplyImmediately=params['apply_immediately'], **modify_args)
        else:
            # Return existing instance details verbatim
            result = dict(DBInstance=instance)

        # Set instance tags
        tags_result = client.list_tags_for_resource(ResourceName=check_instance['DBInstances'][0]['DBInstanceArn'])
        if 'TagList' in tags_result:
            client.remove_tags_from_resource(ResourceName=check_instance['DBInstances'][0]['DBInstanceArn'], TagKeys=[t['Key'] for t in tags_result['TagList']])
            if tags is not None:
                api_args['Tags'] = tags
                client.add_tags_to_resource(ResourceName=check_instance['DBInstances'][0]['DBInstanceArn'], Tags=tags)

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'DBInstanceNotFound':
            api_args['DBInstanceIdentifier'] = params['instance_id']

            if params['cluster_id'] is not None:
                api_args['DBClusterIdentifier'] = params['cluster_id']
            if params['engine'] is not None:
                api_args['Engine'] = params['engine']
            if params['subnet_group'] is not None:
                api_args['DBSubnetGroupName'] = params['subnet_group']
            if tags is not None:
                api_args['Tags'] = tags

            try:
                result = client.create_db_instance(**api_args)
            except (botocore.exceptions.ClientError, boto.exception.BotoServerError), e:
                module.fail_json(msg=str(e), api_args=api_args)

        else:
            module.fail_json(msg=str(e), api_args=api_args)

    except boto.exception.BotoServerError as e:
        module.fail_json(msg=str(e), api_args=api_args)

    if params['wait']:
        wait_timeout = time.time() + params['wait_timeout']
        ready = False
        while not ready and wait_timeout > time.time():
            try:
                check_instance = client.describe_db_instances(DBInstanceIdentifier=params['instance_id'])
                if 'DBInstances' in check_instance and len(check_instance['DBInstances']) == 1:
                    if check_instance['DBInstances'][0]['DBInstanceStatus'].lower() == 'available':
                        ready = True

            except (botocore.exceptions.ClientError, boto.exception.BotoServerError), e:
                pass

            if not ready:
                time.sleep(5)

        if wait_timeout <= time.time():
            if 'DBInstances' in check_instance and len(check_instance['DBInstances']) == 1:
                instance = check_instance['DBInstances'][0]
            else:
                instance = None
            module.fail_json(msg='Timed out waiting for DB instance to become available', instance=instance)

    module.exit_json(result=result)


def main():
    module_args = dict(
        apply_immediately = dict(required=False, type='bool', default=False),
        auto_minor_version_upgrade = dict(required=False, type='bool', default=True),
        availability_zone = dict(required=False, default=None),
        cloudwatch_logs_exports = dict(required=False, default=None),
        cluster_id = dict(required=False),
        copy_tags_to_snapshot = dict(required=False, type='bool', default=True),
        engine = dict(required=False, choices=['aurora'], default='aurora'),
        instance_id = dict(required=True),
        instance_type = dict(required=False),
        monitoring_interval = dict(required=False, type='int', default=0, choices=[0, 1, 5, 10, 15, 30, 60]),
        monitoring_role_arn = dict(required=False, default=None),
        multi_az = dict(required=False, type='bool', default=False),
        option_group = dict(required=False, default=None),
        parameter_group = dict(required=False, default=None),
        performance_insights = dict(required=False, type='bool', default=False),
        preferred_maintenance_window = dict(required=False, default=None),
        promotion_tier = dict(required=False, type='int', default=None),
        publicly_accessible = dict(required=False, type='bool', default=False),
        state = dict(required=False, default='present', choices=['present', 'absent']),
        subnet_group = dict(required=False, default=None),
        tags = dict(required=False, type='dict', default={}),
        wait = dict(required=False, type='bool', default=False),
        wait_timeout = dict(required=False, type='int', default=1200),
    )
    argument_spec = ec2_argument_spec()
    argument_spec.update(module_args)
    module = AnsibleModule(argument_spec=argument_spec)

    args_dict = {arg: module.params.get(arg) for arg in module_args.keys()}
    #module.fail_json(msg='test', args_dict=args_dict)

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 required for this module')

    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        rds = boto3_conn(module, conn_type='client', resource='rds', region=region, endpoint=ec2_url, **aws_connect_kwargs)

    except botocore.exceptions.ClientError, e:
        module.fail_json(msg="Boto3 Client Error - " + str(e))

    if module.params.get('state') == 'present':
        create_db_instance(module, rds, **args_dict)
    elif module.params.get('state') == 'absent':
        terminate_db_instance(module, rds, **args_dict)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
