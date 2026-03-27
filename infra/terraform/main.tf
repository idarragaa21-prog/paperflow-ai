terraform {
  required_version = ">= 1.7.0"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.14"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

resource "kubernetes_namespace" "paperflow" {
  metadata {
    name = var.namespace
  }
}

resource "helm_release" "paperflow_ai" {
  name       = "paperflow-ai"
  namespace  = kubernetes_namespace.paperflow.metadata[0].name
  chart      = "${path.module}/../helm/paperflow-ai"
  depends_on = [kubernetes_namespace.paperflow]
}
