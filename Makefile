# Makefile for managing installation, uninstallation, and cleanup

# Variables
TOOLS_DIR=tools
DEPLOY_DIR=install/deploy
OPERATOR_DIR=install/operator
registry ?= svc
ip ?= 192.168.10.81
namespace ?= np-operator
.PHONY: install uninstall clean

# Install: Run the necessary scripts to install the application
install:
	@echo "Running installation scripts..."
	kubectl apply -f $(OPERATOR_DIR)/crd.yml

	cd $(TOOLS_DIR) && ip=$(ip) ns=$(namespace) sh cert.sh
	kubectl apply -f install
	cd $(TOOLS_DIR) && ip=$(ip) ns=$(namespace) sh registry-webhook.sh $(registry)
	kubectl apply -f $(DEPLOY_DIR)/1-deploy-webhook.yml
	kubectl wait -n np-operator --for=condition=ready pod -l app=np-webhook --timeout=300s
	kubectl apply -f $(DEPLOY_DIR)/2-deploy-operator.yml
	@echo "Installation completed."

# Uninstall: Delete the Kubernetes resources
uninstall:
	@echo "Uninstalling Kubernetes resources..."
	kubectl delete -f $(OPERATOR_DIR)/admission-webhook.yml
	kubectl delete -f $(DEPLOY_DIR)
	kubectl delete -f $(OPERATOR_DIR)/crd.yml
	kubectl delete -f install/role.yml
	@echo "Uninstallation completed."

# Clean: Remove files generated during installation
clean:
	@echo "Cleaning up generated files..."
	cd $(TOOLS_DIR) && rm -rf files/*
	@echo "Cleanup completed."
