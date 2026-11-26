---
name: offensive-cloud-and-containers
description: Offensive testing for AWS/GCP/Azure cloud environments, Kubernetes clusters, Docker container escapes, Linux privilege escalation, CI/CD pipeline poison, and supply chain attacks.
---

# Cloud, Container & Supply Chain Offensive Security Suite

Attacking cloud IAM, container runtimes, Kubernetes RBAC, GitHub Actions pipelines, and software supply chains.

## Modules
### Cicd Pipeline (`offensive-cicd-pipeline`)
---
name: offensive-cicd-pipeline
description: "Comprehensive CI/CD pipeline exploitation methodology covering GitHub Actions injection vectors (expression injection via PR titles and issue bodies, workflow_run event abuse, GITHUB_TOKEN over-scoping, composite action supply chain compromise), Jenkins attack paths (Groovy sandbox escapes, script console remote code execution, Java remoting deserialization, credential store dumping, shared library 

### Cicd Secrets (`offensive-cicd-secrets`)
---
name: offensive-cicd-secrets
description: "Comprehensive secrets extraction methodology targeting CI/CD environments across all major platforms. Covers environment variable extraction from build contexts, exploitation of vault and secrets-manager misconfigurations (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager), runner and agent token abuse for lateral movement, OIDC federation attacks exploiting trust relationship

### Cloud (`offensive-cloud`)
---
name: offensive-cloud
description: "Cloud security attack methodology covering AWS, Azure, and GCP. Includes credential harvesting (IMDS, ~/.aws, env vars, leaked CI secrets, instance roles), enumeration with cloud-specific tools (pacu, ScoutSuite, Prowler, ROADtools, gcp_enum), privilege escalation paths (IAM PassRole, AssumeRole chains, Lambda/Functions privilege flips, Azure Owner-on-self, GCP serviceAccountTokenCreator), persistence techn

### Container Escape (`offensive-container-escape`)
---
name: offensive-container-escape
description: "Container escape and breakout techniques targeting Docker, containerd, and Podman runtimes. Covers privileged container breakout via host filesystem mount and nsenter, Docker socket abuse through /var/run/docker.sock, Linux capability exploitation including CAP_SYS_ADMIN, CAP_SYS_PTRACE, and CAP_NET_ADMIN, cgroup v1 notify_on_release escape, runc CVEs such as CVE-2019-5736 and CVE-2024-21626 Leak

### Dependency Confusion (`offensive-dependency-confusion`)
---
name: offensive-dependency-confusion
description: "Deep-dive offensive methodology for dependency confusion and namespace attacks across all major package ecosystems. Covers npm scope confusion exploiting the gap between public and private scoped packages and .npmrc misconfigurations where registry mappings fail to pin internal scopes exclusively. Addresses PyPI namespace attacks through --extra-index-url resolution ordering, NuGet feed prior

### K8S Attacks (`offensive-k8s-attacks`)
---
name: offensive-k8s-attacks
description: "Kubernetes cluster attack techniques covering the full attack lifecycle from initial foothold in a pod to cluster-wide compromise. Covers service account token theft and impersonation, RBAC misconfiguration exploitation including wildcard permissions and privilege escalation via role binding, direct etcd access for secret extraction, kubelet API abuse on port 10250 and read-only port 10255, pod escape

### Linux Privesc (`offensive-linux-privesc`)
---
name: offensive-linux-privesc
description: "Comprehensive Linux privilege escalation methodology for offensive security engagements. Covers the full attack surface from a low-privilege shell to root: SUID/SGID binary abuse via GTFOBins, Linux capabilities exploitation (cap_setuid, cap_dac_override, cap_dac_read_search), sudo misconfigurations including NOPASSWD rules and Baron Samedit (CVE-2021-3156), cron job abuse through writable scripts, 

### Supply Chain (`offensive-supply-chain`)
---
name: offensive-supply-chain
description: "Comprehensive offensive methodology for software supply chain attacks covering the full kill chain from reconnaissance through exploitation. Addresses dependency confusion across npm, PyPI, and NuGet ecosystems where internal registry override allows an attacker to inject malicious packages that shadow private dependencies. Covers typosquatting techniques for popular packages, compromised package inj

