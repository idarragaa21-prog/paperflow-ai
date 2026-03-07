variable "kubeconfig_path" {
  description = "Path to the kubeconfig file used for deployment"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace for PaperFlow AI"
  type        = string
  default     = "paperflow-ai"
}
