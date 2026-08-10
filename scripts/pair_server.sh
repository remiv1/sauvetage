#!/bin/bash

# dependencies verification
if ! command -v ssh &> /dev/null; then
    echo "ssh command not found. Please install OpenSSH client."
    exit 1
fi
if ! command -v ssh-keygen &> /dev/null; then
    echo "ssh-keygen command not found. Please install OpenSSH client."
    exit 1
fi
if ! command -v ssh-copy-id &> /dev/null; then
    echo "ssh-copy-id command not found. Please install OpenSSH client."
    exit 1
fi
if ! command -V sshpass &> /dev/null; then
    echo "sshpass command not found. Please install sshpass."
    exit 1
fi

# Read user input for server connection details
read -p "Enter your username on server: " USERNAME
read -p "Enter your server IP address or domain name: " SERVER_IP
read -p "Enter the key name for the SSH key (e.g., id_rsa): " KEY_NAME
read -p "Enter the path to your private key file (e.g., /home/<username>/.ssh): " KEY_PATH
read -p "Enter the password of your server (if required): " SERVER_PASSWORD
read -p "Is there a specific port for SSH connection? (default is 22) [y/N]: " PORT_CHOICE
if [[ "$PORT_CHOICE" =~ ^[Yy]$ ]]; then
    read -p "Enter the SSH port number: " SSH_PORT
else
    SSH_PORT=22
fi
SSH_OPTIONS="-p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
ACTUAL_USERNAME=$(whoami)

# Génération of SSH key pair
echo "Generating SSH key pair..."
ssh-keygen -t ed25519 -C "$KEY_NAME" -f $KEY_PATH/$KEY_NAME -N ""
echo
echo "SSH key pair generated:"
echo "Private key: $KEY_PATH/$KEY_NAME"
echo "Public key: $KEY_PATH/$KEY_NAME.pub"

# Create folder on the paired server
echo
echo "Creating .ssh directory on the server..."
sshpass -p "$SERVER_PASSWORD" ssh $SSH_OPTIONS $USERNAME@$SERVER_IP "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
echo
echo "Folder ~/.ssh created on the server with correct permissions."

# Copy the public key to the server
echo
echo "Copying public key to the server..."
sshpass -p "$SERVER_PASSWORD" ssh-copy-id -i $KEY_PATH/$KEY_NAME.pub $SSH_OPTIONS $USERNAME@$SERVER_IP
echo
echo "Public key copied to the server. You can now log in without a password."

# Test the SSH connection to the server
echo
echo "Testing SSH connection to the server..."
ssh -i $KEY_PATH/$KEY_NAME $SSH_OPTIONS $USERNAME@$SERVER_IP "echo 'SSH connection successful!'" ||
{
    echo "SSH connection failed. Please check your credentials and try again."
    exit 1
}
echo
echo "SSH connection to the server is successful. You can now use the SSH key for secure access."
