from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum, unique, auto

import logging
logger = logging.getLogger(__name__)

@unique
class DbtBigQueryConnectionMethod(str, Enum):
    """Defines supported connection method to BigQuery via dbt-bigquery"""
    OAUTH = auto()
    SERVICE_ACCOUNT_KEY = auto()
    SERVICE_ACCOUNT_IMPERSONATION = auto()

@dataclass
class DbtConnectionConfig(ABC):
    """Abstract base class for dbt connection profiles configurations."""

    @abstractmethod()
    def to_dbt_profiles_dict(self) -> Dict:
        pass


@dataclass
class GcpDbtConnectionConfig(DbtConnectionConfig):
    """Data class for dbt connection profiles configurations to GCP."""
    project_id: str
    gcp_region: str
    dataset_id: str
    connection_method: DbtBigQueryConnectionMethod
    service_account_key_path: Optional[str]
    service_account_impersonation_credentials: Optional[str]
    threads: int = 1
    timeout_seconds: int = 600
    priority: str = 'interactive'
    retries: int = 1

    def __init__(self,
                project_id: str,
                gcp_region: str,
                dataset_id: str,
                service_account_key_path: Optional[str],
                impersonation_credentials: Optional[str]):
        if not any(service_account_key_path, impersonation_credentials):
            logger.info("Using Application-Default Credentials (ADC) to connect to GCP...")
            self.connection_method = DbtBigQueryConnectionMethod.OAUTH
        elif all(service_account_key_path, impersonation_credentials):
            raise AssertionError("Either one or neither but not both of service account JSON key or service account impersonation can be used.")
        elif service_account_key_path:
            logger.info("Using exported service account key to connect to GCP...")
            self.service_account_key_path = service_account_key_path
            self.connection_method = DbtBigQueryConnectionMethod.SERVICE_ACCOUNT_KEY
        elif service_account_key_path:
            logger.info("Using service account impersonation via local ADC credentials to connect to GCP...")
            self.service_account_impersonation_credentials = impersonation_credentials
            self.connection_method = DbtBigQueryConnectionMethod.SERVICE_ACCOUNT_IMPERSONATION
        else:
            raise ValueError("Unable to create dbt connection profile for GCP.")
        self.project_id = project_id
        self.gcp_region = gcp_region
        self.dataset_id = dataset_id

    def get_connection_method(self) -> str:
        if self.connection_method == DbtBigQueryConnectionMethod.OAUTH or \
            self.connection_method == DbtBigQueryConnectionMethod.SERVICE_ACCOUNT_IMPERSONATION:
            return 'oauth'
        elif self.connection_method.SERVICE_ACCOUNT_KEY:
            return 'service-account'
        else:
            raise ValueError("Unable to get dbt connection method for GCP.")

    def to_dbt_bigquery_profiles_dict(self) -> Dict:
        profiles_configs = {
            "type": "bigquery",
            "method": self.get_connection_method(),
            "project": self.project_id,
            "dataset": self.dataset_id,
            "location": self.gcp_region,
            "threads": self.threads,
            "timeout_seconds": self.timeout_seconds,
            "priority": self.priority,
            "retries": self.retries
        }
        if self.connection_method == DbtBigQueryConnectionMethod.SERVICE_ACCOUNT_KEY:
            assert Path(self.service_account_key_path).is_file()
            profiles_configs['keyfile'] = self.service_account_key_path
        elif self.connection_method == DbtBigQueryConnectionMethod.SERVICE_ACCOUNT_IMPERSONATION:
            assert self.service_account_impersonation_credentials
            assert profiles_configs['method'] == 'oauth'
            profiles_configs['impersonate_service_account'] = self.service_account_impersonation_credentials
        else:
            assert profiles_configs['method'] == 'oauth'
        return profiles_configs

    def to_dbt_profiles_dict(self) -> Dict:
        return self.to_dbt_bigquery_profiles_dict()
