#!/usr/bin/env bash

set -eux

# Every host gets its own worker. Workers must not consume a per-process limited resource for their lifetime,
# e.g. musl libc caps named semaphores at 256 per process, which previously limited forks to ~80.
ansible-playbook -i hosts -f 100 test.yml "$@"
