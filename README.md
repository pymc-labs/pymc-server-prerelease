# Quickstart

## Installation

Install this library from PiPy `pip3 install pymc-server`

If you want to install this library from source:
```bash
git clone https://github.com/pymc-dev/PyMC-Server
cd PyMC-Server

pip3 install . 
# run 'pip3 install -e .' if you want to be able to edit the code
```

### Setting up a cloud: Google Cloud

1. Run `pymcs check` to see if you already have credentials setup. If you see a green checkmark for GCP (Google Cloud Platform), skip to the next section
2. Install the google cloud SDK and authenticate.
  ```bash
  conda install -c conda-forge google-cloud-sdk
  gcloud init

  # Run this if you don't have a credentials file.
  # This will generate ~/.config/gcloud/application_default_credentials.json.
  gcloud auth application-default login
  ```
  > Tip:
  > If you are using multiple GCP projects, list all the projects by gcloud projects list and activate one by gcloud config set project <PROJECT_ID> (see GCP docs).

3. Follow the link to Google and authorize the Google Cloud SDK. This will create and persist credentials on your local computer. Running pymc-server commands via Google Cloud will introduce cost to your Google Cloud bill according to the VMs provisioned by your configuration (see next section).

  ![Gcloud SDK Auth](./assets/gcloud_auth.png)

  Follow through the rest of the GCP configuration in your terminal.


### Status of your deployments

To check the status of all your deployments run `pymcs status`. A table is printed to your terminal.

```bash
❯ pymcs status
Clusters
NAME  LAUNCHED      RESOURCES                 STATUS  AUTOSTOP  COMMAND
tc    5 months ago  1x Kubernetes(2CPU--2GB)  UP      -         pymcs launch -c tc hello_sk...

Managed jobs
No in-progress managed jobs. (See: pymcs jobs -h)

Services
No live services. (See: pymcs serve -h)
```
