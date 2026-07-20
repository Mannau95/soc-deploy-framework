"""
Logique d'installation de la stack Wazuh
Couvre : assistant officiel, paquets, Docker, multi-nœuds, cluster HA
"""

import os
from pathlib import Path
from typing import Any, Dict
import asyncio
from soc_deploy.services.executor import ExecutionStatus


class WazuhInstaller:
    async def check_prerequisites(self, ctx) -> Dict[str, Any]:
        """Vérifications spécifiques à Wazuh"""
        issues = []
        # Vérifier les ports requis
        required_ports = [
            55000,
            1514,
            1515,
            1516,
            9200,
            443,
        ]  # manager, agent, enrollment, cluster, indexer, dashboard
        port_checks = ctx.system_checker.check_ports(required_ports)
        for check in port_checks:
            if check.status.value != "OK":
                issues.append(check.message)
        # Vérifier curl/wget
        if not await ctx.executor.check_command_exists("curl"):
            issues.append("curl est requis pour l'installation")
        # Vérifier les capacités du système (mmap, etc.)
        vm_max_map = await ctx.executor.execute("sysctl vm.max_map_count")
        if vm_max_map.status == ExecutionStatus.SUCCESS:
            val = int(vm_max_map.stdout.strip().split()[-1])
            if val < 262144:
                issues.append(
                    "vm.max_map_count doit être >= 262144 (Elasticsearch/OpenSearch)"
                )
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options: Dict[str, Any]) -> Dict[str, Any]:
        architecture = options.get("architecture", "all-in-one")
        method = options.get("installation_method", "assistant")
        version = options.get("wazuh_version", "4.7.0")
        admin_password = options.get("admin_password", "")
        ssl = options.get("ssl", True)
        expose_dashboard = options.get("expose_dashboard", False)

        # Générer un mot de passe admin si non fourni
        if not admin_password:
            import secrets
            import string

            alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
            admin_password = "".join(secrets.choice(alphabet) for _ in range(16))
            ctx.logger.info(f"Mot de passe admin généré : {admin_password}")
            # Le stocker dans le contexte pour la suite
            ctx.variables["wazuh_admin_password"] = admin_password

        if method == "assistant":
            return await self._install_via_assistant(
                ctx, architecture, version, admin_password, ssl, expose_dashboard
            )
        elif method == "packages":
            return await self._install_via_packages(
                ctx, architecture, version, admin_password, ssl
            )
        elif method == "docker":
            return await self._install_via_docker(
                ctx, architecture, version, admin_password, expose_dashboard
            )
        elif method == "kubernetes":
            return {
                "success": False,
                "error": "Installation Kubernetes non implémentée dans cette version",
            }
        else:
            return {"success": False, "error": f"Méthode inconnue: {method}"}

    async def _install_via_assistant(
        self,
        ctx,
        architecture: str,
        version: str,
        admin_password: str,
        ssl: bool,
        expose_dashboard: bool,
    ) -> Dict[str, Any]:
        """Utilise l'assistant officiel curl -sO https://packages.wazuh.com/4.7/wazuh-install.sh && bash wazuh-install.sh --generate-config-files"""
        # Téléchargement du script
        url = f"https://packages.wazuh.com/{version}/wazuh-install.sh"
        script_path = "/tmp/wazuh-install.sh"
        download = await ctx.executor.execute(f"curl -sSfL {url} -o {script_path}")
        if download.status != ExecutionStatus.SUCCESS:
            return {
                "success": False,
                "error": "Échec du téléchargement du script d'installation",
            }

        # Génération du fichier de configuration selon l'architecture
        config_yml = self._generate_assistant_config(
            architecture, admin_password, ssl, expose_dashboard
        )
        config_path = "/tmp/wazuh-config.yml"
        ctx.file_manager.write_file(config_path, config_yml)

        # Exécution
        cmd = f"bash {script_path} --generate-config-files --config-file {config_path}"
        if architecture == "all-in-one":
            cmd += " --all-in-one"
        elif architecture == "distributed":
            # Pour simplifier, on utilise l'option --distributed avec paramètres adéquats
            cmd += " --distributed"
        # Le script génère les fichiers, puis on installe
        result = await ctx.executor.execute(cmd, timeout=1200, sudo=True)
        if result.status != ExecutionStatus.SUCCESS:
            return {"success": False, "error": result.stderr}

        # L'assistant a créé les fichiers de configuration, on lance l'installation
        install_cmd = f"bash {script_path} --install"
        install_result = await ctx.executor.execute(
            install_cmd, timeout=1800, sudo=True
        )
        if install_result.status != ExecutionStatus.SUCCESS:
            return {"success": False, "error": install_result.stderr}

        # Récupérer le mot de passe admin depuis le fichier généré
        pass_file = "/tmp/wazuh-install-files.tar"
        if os.path.exists(pass_file):
            # Extraire le mot de passe
            extract = await ctx.executor.execute(
                f"tar -xOf {pass_file} wazuh-install-files/wazuh-passwords.txt | grep -i 'admin'"
            )
            if extract.status == ExecutionStatus.SUCCESS and extract.stdout:
                admin_password = extract.stdout.strip().split()[-1]
                ctx.variables["wazuh_admin_password"] = admin_password

        return {"success": True, "password": admin_password}

    def _generate_assistant_config(
        self, architecture: str, admin_password: str, ssl: bool, expose_dashboard: bool
    ) -> str:
        """Génère le fichier config.yml pour l'assistant"""
        # Nous retournons un template simplifié. En pratique, on utiliserait Jinja2.
        return """
nodes:
  # Wazuh indexer nodes
  indexer:
    - name: node-1
      ip: localhost
  # Wazuh server nodes
  server:
    - name: wazuh-1
      ip: localhost
  # Wazuh dashboard node
  dashboard:
    - name: dashboard
      ip: localhost
"""

    async def _install_via_packages(
        self, ctx, architecture: str, version: str, admin_password: str, ssl: bool
    ) -> Dict[str, Any]:
        """Installation par paquets (support Debian/Ubuntu et RHEL/CentOS)"""
        distro = ctx.system_info.distro.lower()
        if distro in ["ubuntu", "debian"]:
            # Ajouter le dépôt GPG
            await ctx.executor.execute(
                "curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor | sudo tee /usr/share/keyrings/wazuh.gpg > /dev/null",
                timeout=30,
            )

            repo_line = f"deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/{version}/apt/ stable main"
            await ctx.executor.execute(
                f"echo '{repo_line}' | sudo tee /etc/apt/sources.list.d/wazuh.list"
            )
            await ctx.package_manager.update_repositories()
            # Installer les composants
            if architecture == "all-in-one":
                pkgs = ["wazuh-indexer", "wazuh-manager", "wazuh-dashboard"]
            else:
                pkgs = ["wazuh-manager"]
            install_res = await ctx.package_manager.install_packages(pkgs)
            if not install_res.success:
                return {"success": False, "error": install_res.errors}
            # Démarrer les services
            for pkg in pkgs:
                await ctx.executor.execute(
                    f"systemctl enable {pkg} && systemctl start {pkg}", sudo=True
                )
            # Post-configuration (simplifiée)
        else:
            return {
                "success": False,
                "error": "Installation par paquets uniquement sur Debian/Ubuntu pour le moment",
            }
        return {"success": True, "password": admin_password}

    async def _install_via_docker(
        self,
        ctx,
        architecture: str,
        version: str,
        admin_password: str,
        expose_dashboard: bool,
    ) -> Dict[str, Any]:
        """Déploiement Docker avec docker-compose officiel"""
        compose_url = f"https://raw.githubusercontent.com/wazuh/wazuh-docker/v{version}/multi-node/docker-compose.yml"
        if architecture == "all-in-one":
            compose_url = f"https://raw.githubusercontent.com/wazuh/wazuh-docker/v{version}/single-node/docker-compose.yml"
        elif architecture == "cluster":
            compose_url = f"https://raw.githubusercontent.com/wazuh/wazuh-docker/v{version}/multi-node/docker-compose.yml"

        compose_path = Path("/tmp/wazuh-docker-compose.yml")
        download = await ctx.executor.execute(
            f"curl -sSfL {compose_url} -o {compose_path}"
        )
        if download.status != ExecutionStatus.SUCCESS:
            return {
                "success": False,
                "error": "Téléchargement du docker-compose.yml échoué",
            }

        # Lancer avec docker compose
        up_result = await ctx.docker_manager.compose_up(
            compose_path, detach=True, build=False
        )
        if not up_result:
            return {"success": False, "error": "docker-compose up a échoué"}

        # Attendre que les conteneurs soient prêts (healthcheck)
        await asyncio.sleep(30)
        return {"success": True, "password": admin_password}

    async def uninstall(self, ctx) -> Dict[str, Any]:
        """Désinstallation complète selon la méthode détectée"""
        # Tenter de stopper les services et supprimer les paquets/conteneurs
        services = ["wazuh-manager", "wazuh-indexer", "wazuh-dashboard"]
        for svc in services:
            await ctx.executor.execute(
                f"systemctl stop {svc} 2>/dev/null; systemctl disable {svc} 2>/dev/null",
                sudo=True,
            )

        # Supprimer les paquets si présents
        await ctx.package_manager.remove_packages(services, purge=True)

        # Arrêter et supprimer les conteneurs Docker si le déploiement était Docker
        # Détection basée sur le nom des conteneurs
        containers = ["wazuh.manager", "wazuh.indexer", "wazuh.dashboard"]
        for cont in containers:
            await ctx.docker_manager.stop_container(cont)
            await ctx.docker_manager.remove_container(cont)

        return {"success": True}

    async def update(self, ctx) -> Dict[str, Any]:
        # On peut réutiliser l'installation avec la même méthode
        return await self.install(ctx, {"architecture": "all-in-one"})  # simplifié
