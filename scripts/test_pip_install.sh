#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -o errexit
set -o nounset
set -o pipefail

set -x

# get diagnostic info
which python3
python3 --version
python3 -m pip --version

# create temporary virtualenv
python3 -m venv /tmp/clouddq_test_env
source /tmp/clouddq_test_env/bin/activate

# install clouddq wheel into temporary env
python3 -m pip install .

# set variables
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export CLOUDDQ_BIGQUERY_DATASET="dq_test"
export CLOUDDQ_BIGQUERY_REGION="EU"
export IMPERSONATION_SERVICE_ACCOUNT="argo-svc@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

# smoke test clouddq commands
python3 clouddq --help
python3 clouddq ALL configs --dbt_profiles_dir=tests/resources/test_dbt_profiles_dir --debug --dry_run --skip_sql_validation
python3 clouddq ALL configs --dbt_profiles_dir=tests/resources/test_dbt_profiles_dir --debug --dbt_path=dbt --dry_run --skip_sql_validation

# test clouddq in isolated directory with minimal file dependencies
TEST_DIR=/tmp/clouddq-test-pip
rm -rf "$TEST_DIR"
mkdir "$TEST_DIR"
cp -r configs "$TEST_DIR"
cp tests/resources/test_dbt_profiles_dir/profiles.yml "$TEST_DIR"
cd "$TEST_DIR"
python3 -m clouddq ALL configs --dbt_profiles_dir="$TEST_DIR" --debug --dry_run --skip_sql_validation

# test clouddq with direct connection profiles
python3 -m clouddq ALL configs \
    --gcp_project_id=$GOOGLE_CLOUD_PROJECT \
    --gcp_bq_dataset_id=$CLOUDDQ_BIGQUERY_DATASET \
    --gcp_region_id=$CLOUDDQ_BIGQUERY_REGION \
    --debug \
    --dry_run \
    --skip_sql_validation

# test clouddq with exported service account key if exists
if [[ -f "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
    python3 -m clouddq ALL configs \
        --gcp_project_id=$GOOGLE_CLOUD_PROJECT \
        --gcp_bq_dataset_id=$CLOUDDQ_BIGQUERY_DATASET \
        --gcp_region_id=$CLOUDDQ_BIGQUERY_REGION \
        --gcp_service_account_key_path=$GOOGLE_APPLICATION_CREDENTIALS \
        --debug \
        --dry_run \
        --skip_sql_validation
fi

# test clouddq with service account impersonation
if [[ -f "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
    python3 -m clouddq ALL configs \
        --gcp_project_id=$GOOGLE_CLOUD_PROJECT \
        --gcp_bq_dataset_id=$CLOUDDQ_BIGQUERY_DATASET \
        --gcp_region_id=$CLOUDDQ_BIGQUERY_REGION \
        --gcp_impersonation_credentials=$IMPERSONATION_SERVICE_ACCOUNT \
        --debug \
        --dry_run \
        --skip_sql_validation
fi