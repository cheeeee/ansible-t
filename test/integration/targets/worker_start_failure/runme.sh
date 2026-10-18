#!/usr/bin/env bash

set -eux

# A failure to create or start a worker must abort the run instead of silently skipping the task for that host.
# The 3rd worker fails during the first task; the 6th worker replaces a finished worker during the second task.
for failure in start:3 init:3 init:6; do
    FAIL_WORKER="$failure" ANSIBLE_STRATEGY_PLUGINS=./strategy_plugins ansible-playbook -i hosts -f 5 test.yml "$@" > out.txt 2>&1 && rc=$? || rc=$?

    cat out.txt

    [ "$rc" -eq 1 ]
    grep -q "Unable to start a worker for host" out.txt
    grep -q "simulated worker ${failure%:*} failure" out.txt
    grep -q "should not run" out.txt && exit 1
    grep -q "Unexpected Exception" out.txt && exit 1
done

echo PASS
