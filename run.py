import logging
import sys

from src.workers import Signer, Validator


def print_help():
    print(
        f'Usage:\n  {sys.orig_argv[0]} {sys.argv[0]} WORKER_TYPE [WORKER_NAME]\nExample:'
        f'\n  {sys.orig_argv[0]} {sys.argv[0]} validator'
        f'\n  {sys.orig_argv[0]} {sys.argv[0]} signer'
        f'\n  {sys.orig_argv[0]} {sys.argv[0]} signer lister'
    )


if '-h' in sys.argv or '--help' in sys.argv:
    print_help()
    sys.exit(0)

if len(sys.argv) < 2:
    print_help()
    sys.exit(1)

worker_name = None
worker_type = sys.argv[1]
if len(sys.argv) > 2:
    worker_name = sys.argv[2]

workers = {
    'validator': Validator,
    'signer': Signer
}

if worker_type not in workers:
    print(f'No worker named {worker_type}')
    sys.exit(1)

log = logging.getLogger('worker')
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
log.addHandler(handler)
log.setLevel(logging.DEBUG)

worker = workers[worker_type](name=worker_name)
worker.listen()
