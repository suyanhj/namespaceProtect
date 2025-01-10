# Makefile for managing installation, uninstallation, and cleanup

# Variables
TOOLS_DIR=tools
DEPLOY_DIR=install/deploy
OPERATOR_DIR=install/operator

.PHONY: install uninstall clean

# Install: Run the necessary scripts to install the application
install:
	@echo "Running installation scripts..."
	kubectl apply -f $(OPERATOR_DIR)/crd.yml
	cd $(TOOLS_DIR) && sh cert.sh
	kubectl apply -f $(DEPLOY_DIR)/1-ns.yml
	cd $(TOOLS_DIR) && sh registry-webhook.sh
	kubectl apply -f $(DEPLOY_DIR)
	@echo "Installation completed."

# Uninstall: Delete the Kubernetes resources
uninstall:
	@echo "Uninstalling Kubernetes resources..."
	kubectl delete -f $(OPERATOR_DIR)/admission-webhook.yml
	kubectl delete -f $(DEPLOY_DIR)
	kubectl delete -f $(OPERATOR_DIR)/crd.yml
	@echo "Uninstallation completed."

# Clean: Remove files generated during installation
clean:
	@echo "Cleaning up generated files..."
	cd $(TOOLS_DIR) && rm -rf files/*
	@echo "Cleanup completed."
