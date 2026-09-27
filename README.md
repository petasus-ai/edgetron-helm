# Edgetron
Edgetron is an abstraction layer used for provisioning virtual infrastructure in the purpose of hosting Kubernetes service. Edgetron exposes MM3 interface to MEPM OP for northbound, to southbound, it invokes standarized cluster-api to provision Kubernetes cluster.

## TL;DR;

```console
$ git clone https://github.com/petasus-ai/edgetron-helm.git
$ helm install my-edgetron edgetron-helm
```

## Introduction

This chart bootstraps a [edgetron](https://gitlab.tde.sktelecom.com/PETASUS/edgetron) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

Edgetron charts can be used with [Kubeapps](https://kubeapps.com/) for deployment and management of Helm Charts in clusters. 

## Prerequisites

- Kubernetes 1.12+
- Helm 2.12+ or Helm 3.0-beta3+

## Installing the Chart

To install the chart with the release name `my-edgetron`:

```console
$ helm install my-edgetron edgetron-helm
```

These commands deploy edgetron on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Uninstalling the Chart

To uninstall/delete the `my-edgetron` deployment:

```console
$ helm delete my-edgetron
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Parameters

The following tables lists the configurable parameters of the SONA chart and their default values.
| Parameter                            | Description                                                            | Default                                  |
|--------------------------------------|------------------------------------------------------------------------|------------------------------------------|
| `edgetronImage.registry`             | Edgetron container image registry                                      | `registry.tde.sktelecom.com`             |
| `edgetronImage.repository`           | Edgetron container image repository                                    | `petasus/edgetron`                       |
| `edgetronImage.tag`                  | Edgetron container image tag                                           | `latest`                                 |
| `edgetronImage.pullPolicy`           | Edgetron container image pull policy                                   | `IfNotPresent`                           |
| `edgetronWatcherImage.repository`    | Edgetron watcher container image repository                            | `petasus/edgetron/watcher`               |
| `vmEventImage.repository`            | VM event operator container image repository                           | `petasus/vm-event-operator`              |
| `replicaCount`                       | Edgetron POD replica number                                            | `1`                                      |
| `service.type`                       | Edgetron service type                                                  | `NodePort`                               |
| `service.port`                       | Edgetron service port number                                           | `8080`                                   |
| `service.nodePort`                   | Edgetron service node port number                                      | `30080`                                  |
| `auth.existingSecret`                | Secret with the keys `jwt-secret`, `username`, `password`; the chart then creates none | `""`                     |
| `auth.username`                      | Account ks-apiserver takes edgetron tokens with                        | `edgetron`                               |
| `auth.password`                      | Its password; empty keeps the Secret's current one or generates one    | `""`                                     |
| `auth.jwtSecret`                     | Key edgetron signs tokens with; empty keeps the current one or generates one | `""`                               |
| `auth.accessTokenTTLSeconds`         | Access token lifetime                                                  | `3600`                                   |
| `auth.refreshTokenTTLSeconds`        | Refresh token lifetime                                                 | `86400`                                  |
| `networkPolicy.enabled`              | Let only ks-apiserver and the Gateway reach edgetron                   | `true`                                   |
| `networkPolicy.apiserver.namespace`  | Namespace of ks-apiserver (ks-installer installs it in petasus-system)  | `petasus-system`                         |
| `networkPolicy.apiserver.podLabels`  | Labels of the ks-apiserver pods                                        | `app: ks-apiserver`                      |
| `networkPolicy.gateway.podLabels`    | Labels of the Gateway's data plane pods                                | `gateway.networking.k8s.io/gateway-name: edgetron-gateway` |
| `networkPolicy.extraIngressFrom`     | More NetworkPolicy peers allowed to reach edgetron                     | `[]`                                     |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```console
$ helm install my-edgetron \
  --set service.type=ClusterIP edgetron-helm
```

The above command sets the default service type as ClusterIP.

Alternatively, a YAML file that specifies the values for the parameters can be provided while installing the chart. For example,

```console
$ helm install my-edgetron -f values.yaml edgetron-helm
```

> **Tip**: You can use the default [values.yaml](values.yaml)

## Authentication and access

ks-apiserver is the only caller of the edgetron API. It takes a token with the
account in the Secret `edgetron-auth` (keys `jwt-secret`, `username`,
`password`), which it reads itself, and edgetron signs tokens with
`jwt-secret`. The first install generates the password and the signing key;
upgrades keep them.

A NetworkPolicy lets only ks-apiserver and the Gateway reach edgetron, and the
Gateway routes nothing but the API docs (`/edgetron/docs`, `/edgetron/redoc`,
`/edgetron/v1/openapi.json`, `/edgetron/static`) to it.

Upgrading a cluster that runs an older edgetron or ks-apiserver: an older
edgetron image ignores the Secret and keeps the built-in account, and an older
ks-apiserver keeps its own, so a generated account would lock them out of
each other. Do the first upgrade with the current account, and rotate once
both images are the new ones:

```console
$ helm upgrade edgetron edgetron-helm -n edgestack-system --reuse-values \
    --set auth.password=<current password> --set auth.jwtSecret=<current signing key>
```

To rotate the account and the signing key, delete the Secret, or set new
`auth.password` and `auth.jwtSecret`, and upgrade. Clear values set earlier,
which `--reuse-values` would otherwise keep:

```console
$ kubectl -n edgestack-system delete secret edgetron-auth
$ helm upgrade edgetron edgetron-helm -n edgestack-system --reuse-values \
    --set auth.password= --set auth.jwtSecret=
```

The Secret's checksum on the pod template restarts edgetron with the new
values. ks-apiserver needs no restart: its old token is refused, and it takes
a new one with the account it reads from the Secret. While the pods roll, old
and new pods sign with different keys, so a few requests may be refused and
retried.

