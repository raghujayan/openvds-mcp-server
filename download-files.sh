#!/bin/bash
echo "Files to copy to your Mac:"
echo ""
echo "Essential files for Docker deployment:"
for file in Dockerfile docker-compose.yml requirements.txt run-docker.sh DOCKER.md README.md; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done
echo ""
echo "Source code:"
for file in src/*.py test_server.py; do
  if [ -f "$file" ]; then
    echo "  - $file"
  fi
done
