# import logging, sys
#
# def configure_logging(level=logging.INFO):
#     root = logging.getLogger()
#     root.setLevel(level)
#     fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
#     sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt)
#     root.handlers.clear(); root.addHandler(sh)
