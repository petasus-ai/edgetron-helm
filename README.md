# Edgetron
Edgetron is an abstraction layer used for provisioning virtual infrastructure in the purpose of hosting Kubernetes service. Edgetron exposes MM3 interface to MEPM OP for northbound, to southbound, it invokes standarized cluster-api to provision Kubernetes cluster.

## TL;DR;

```console
$ git clone https://github.com/sonaproject/edgetron-helm.git
$ helm install my-edgetron edgetron-helm
```

## Introduction

This chart bootstraps a [edgetron](https://github.com/sonaproject/edgetron) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

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
| `images.registry`                    | Edgetron container image registry                                      | `opensona/registry.gitlab.com`           |
| `images.repository`                  | Edgetron container image repository                                    | `sonaproject/edgetron`                   |
| `images.tag`                         | Edgetron container image tag                                           | `latest`                                 |         
| `images.pullPolicy`                  | Edgetron container image pull policy                                   | `Always`                                 |
| `replicaCount`                       | Edgetron POD replica number                                            | `1`                                      |
| `service.type`                       | Edgetron service type                                                  | `NodePort`                               |
| `service.port`                       | Edgetron service port number                                           | `8080`                                   |
| `service.nodePort`                   | Edgetron service node port number                                      | `30080`                                  |

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

