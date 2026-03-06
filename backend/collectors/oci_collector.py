from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.models.cost import ResourceRecord
from backend.utils.config import settings


class OCICollector:
    """Collects OCI resources with low API pressure.

    Uses OCI SDK when credentials are available. Falls back to sample data to keep
    local/docker testing easy.
    """

    async def collect_inventory(self) -> list[ResourceRecord]:
        try:
            import oci  # noqa: PLC0415

            config = oci.config.from_file(file_location=settings.oci_config_file, profile_name=settings.oci_profile)
            identity = oci.identity.IdentityClient(config)
            tenancy_id = config["tenancy"]
            compartments = self._list_compartments(identity, tenancy_id)
            resources: list[ResourceRecord] = []
            for region in settings.oci_regions.split(","):
                resources.extend(await self._collect_region_resources(config, tenancy_id, region.strip(), compartments))
            return resources
        except Exception:
            return self._sample_inventory()

    def _list_compartments(self, identity: Any, tenancy_id: str) -> list[dict[str, str]]:
        items = identity.list_compartments(tenancy_id, compartment_id_in_subtree=True).data
        return [{"id": tenancy_id, "name": "root"}] + [{"id": c.id, "name": c.name} for c in items]

    async def _collect_region_resources(
        self,
        config: dict[str, Any],
        tenancy_id: str,
        region: str,
        compartments: list[dict[str, str]],
    ) -> list[ResourceRecord]:
        import oci  # noqa: PLC0415

        regional_config = dict(config)
        regional_config["region"] = region
        compute = oci.core.ComputeClient(regional_config)
        block = oci.core.BlockstorageClient(regional_config)
        lb = oci.load_balancer.LoadBalancerClient(regional_config)
        db = oci.database.DatabaseClient(regional_config)
        containers = oci.container_engine.ContainerEngineClient(regional_config)
        obj = oci.object_storage.ObjectStorageClient(regional_config)
        file_storage = oci.file_storage.FileStorageClient(regional_config)

        records: list[ResourceRecord] = []
        for compartment in compartments:
            cid = compartment["id"]
            cname = compartment["name"]
            records.extend(self._collect_compute(compute, block, cid, cname, region, tenancy_id))
            records.extend(self._collect_database(db, cid, cname, region, tenancy_id))
            records.extend(self._collect_lb(lb, cid, cname, region, tenancy_id))
            records.extend(self._collect_oke(containers, cid, cname, region, tenancy_id))
            records.extend(self._collect_storage(obj, file_storage, block, tenancy_id, cid, cname, region))
        return records

    def _collect_compute(self, compute: Any, block: Any, compartment_id: str, compartment_name: str, region: str, tenancy: str) -> list[ResourceRecord]:
        items = compute.list_instances(compartment_id=compartment_id).data
        out: list[ResourceRecord] = []
        for i in items:
            out.append(ResourceRecord(
                tenancy=tenancy,
                region=region,
                compartment=compartment_name,
                resource_type="compute_instance",
                resource_id=i.id,
                resource_name=i.display_name,
                lifecycle_state=i.lifecycle_state,
                creation_time=i.time_created,
                tags=self._tags(i),
                attributes={"shape": i.shape, "ocpus": float(getattr(i.shape_config, "ocpus", 1) or 1), "memory_gb": float(getattr(i.shape_config, "memory_in_gbs", 1) or 1), "boot_volume_gb": 50},
            ))
        return out

    def _collect_database(self, db: Any, compartment_id: str, compartment_name: str, region: str, tenancy: str) -> list[ResourceRecord]:
        out: list[ResourceRecord] = []
        for system in db.list_db_systems(compartment_id=compartment_id).data:
            out.append(ResourceRecord(
                tenancy=tenancy,
                region=region,
                compartment=compartment_name,
                resource_type="db_system",
                resource_id=system.id,
                resource_name=system.display_name,
                lifecycle_state=system.lifecycle_state,
                creation_time=system.time_created,
                tags=self._tags(system),
                attributes={"ocpus": float(system.cpu_core_count or 1)},
            ))
        for adb in db.list_autonomous_databases(compartment_id=compartment_id).data:
            out.append(ResourceRecord(
                tenancy=tenancy,
                region=region,
                compartment=compartment_name,
                resource_type="autonomous_database",
                resource_id=adb.id,
                resource_name=adb.display_name,
                lifecycle_state=adb.lifecycle_state,
                creation_time=adb.time_created,
                tags=self._tags(adb),
                attributes={"ocpus": float(adb.cpu_core_count or 1)},
            ))
        for exa in db.list_cloud_exadata_infrastructures(compartment_id=compartment_id).data:
            out.append(ResourceRecord(
                tenancy=tenancy,
                region=region,
                compartment=compartment_name,
                resource_type="exadata_infrastructure",
                resource_id=exa.id,
                resource_name=exa.display_name,
                lifecycle_state=exa.lifecycle_state,
                creation_time=exa.time_created,
                tags=self._tags(exa),
                attributes={"storage_count": float(getattr(exa, "storage_count", 1) or 1)},
            ))
        return out

    def _collect_lb(self, lb: Any, compartment_id: str, compartment_name: str, region: str, tenancy: str) -> list[ResourceRecord]:
        return [
            ResourceRecord(
                tenancy=tenancy,
                region=region,
                compartment=compartment_name,
                resource_type="load_balancer",
                resource_id=x.id,
                resource_name=x.display_name,
                lifecycle_state=x.lifecycle_state,
                creation_time=x.time_created,
                tags=self._tags(x),
                attributes={},
            )
            for x in lb.list_load_balancers(compartment_id=compartment_id).data
        ]

    def _collect_oke(self, ce: Any, compartment_id: str, compartment_name: str, region: str, tenancy: str) -> list[ResourceRecord]:
        return [
            ResourceRecord(
                tenancy=tenancy,
                region=region,
                compartment=compartment_name,
                resource_type="oke_cluster",
                resource_id=x.id,
                resource_name=x.name,
                lifecycle_state=x.lifecycle_state,
                creation_time=x.time_created,
                tags=self._tags(x),
                attributes={},
            )
            for x in ce.list_clusters(compartment_id=compartment_id).data
        ]

    def _collect_storage(self, obj: Any, fss: Any, block: Any, tenancy_id: str, compartment_id: str, compartment_name: str, region: str) -> list[ResourceRecord]:
        out: list[ResourceRecord] = []
        ns = obj.get_namespace(compartment_id=tenancy_id).data
        for b in obj.list_buckets(namespace_name=ns, compartment_id=compartment_id).data:
            out.append(ResourceRecord(tenancy=tenancy_id, region=region, compartment=compartment_name, resource_type="object_bucket", resource_id=b.id, resource_name=b.name, lifecycle_state="ACTIVE", creation_time=b.time_created, tags=self._tags(b), attributes={"size_gb": 10}))
        for fs in fss.list_file_systems(compartment_id=compartment_id).data:
            out.append(ResourceRecord(tenancy=tenancy_id, region=region, compartment=compartment_name, resource_type="file_storage", resource_id=fs.id, resource_name=fs.display_name, lifecycle_state=fs.lifecycle_state, creation_time=fs.time_created, tags=self._tags(fs), attributes={"size_gb": 100}))
        for vol in block.list_volumes(compartment_id=compartment_id).data:
            out.append(ResourceRecord(tenancy=tenancy_id, region=region, compartment=compartment_name, resource_type="block_volume", resource_id=vol.id, resource_name=vol.display_name, lifecycle_state=vol.lifecycle_state, creation_time=vol.time_created, tags=self._tags(vol), attributes={"size_gb": float(vol.size_in_gbs or 50)}))
        for bvol in block.list_boot_volumes(compartment_id=compartment_id).data:
            out.append(ResourceRecord(tenancy=tenancy_id, region=region, compartment=compartment_name, resource_type="boot_volume", resource_id=bvol.id, resource_name=bvol.display_name, lifecycle_state=bvol.lifecycle_state, creation_time=bvol.time_created, tags=self._tags(bvol), attributes={"size_gb": float(bvol.size_in_gbs or 50)}))
        for bkp in block.list_volume_backups(compartment_id=compartment_id).data:
            out.append(ResourceRecord(tenancy=tenancy_id, region=region, compartment=compartment_name, resource_type="volume_backup", resource_id=bkp.id, resource_name=bkp.display_name, lifecycle_state=bkp.lifecycle_state, creation_time=bkp.time_created, tags=self._tags(bkp), attributes={"size_gb": float(bkp.size_in_gbs or 10)}))
        return out

    def _sample_inventory(self) -> list[ResourceRecord]:
        now = datetime.now(UTC)
        return [
            ResourceRecord(tenancy="sample-tenancy", region="us-ashburn-1", compartment="prod", resource_type="compute_instance", resource_id="ocid1.instance.sample", resource_name="prod-app-server", lifecycle_state="RUNNING", creation_time=now, tags={"env": "prod"}, attributes={"ocpus": 2, "memory_gb": 16, "boot_volume_gb": 100, "block_volume_gb": 200, "backup_gb": 50}),
            ResourceRecord(tenancy="sample-tenancy", region="us-ashburn-1", compartment="prod", resource_type="autonomous_database", resource_id="ocid1.autonomousdatabase.sample", resource_name="orders-adb", lifecycle_state="AVAILABLE", creation_time=now, tags={"env": "prod"}, attributes={"ocpus": 2}),
            ResourceRecord(tenancy="sample-tenancy", region="us-ashburn-1", compartment="shared", resource_type="load_balancer", resource_id="ocid1.loadbalancer.sample", resource_name="public-lb", lifecycle_state="ACTIVE", creation_time=now, tags={"tier": "edge"}, attributes={}),
            ResourceRecord(tenancy="sample-tenancy", region="us-ashburn-1", compartment="shared", resource_type="object_bucket", resource_id="ocid1.bucket.sample", resource_name="logs-bucket", lifecycle_state="ACTIVE", creation_time=now, tags={"team": "platform"}, attributes={"size_gb": 250}),
        ]

    def _tags(self, item: Any) -> dict[str, str]:
        freeform = getattr(item, "freeform_tags", {}) or {}
        defined = getattr(item, "defined_tags", {}) or {}
        flattened = {f"{ns}.{k}": str(v) for ns, fields in defined.items() for k, v in fields.items()}
        return {**{k: str(v) for k, v in freeform.items()}, **flattened}
