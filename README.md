# Ansible RDS Cluster Modules

These are drop-in modules for Ansible 2.3+ which provide the following:

- **rds_cluster** - can create a new RDS cluster or restore from a cluster snapshot
- **rds_cluster_instance** - can create a cluster instance for an existing cluster
- **rds_cluster_snapshot_facts** - can search and return details about RDS cluster snapshots

These modules are specifically for working with RDS Clusters, and have only been tested with Aurora.

For regular RDS instances you should look at Ansible's built-in modules.

These are provided in the event they might be of use. I will not be submitting them to the Ansible project for inclusion but you are welcome to do so.

Please read the module sources for usage information. Note that not all functionality is provided but the modules are idempotent as provided.
