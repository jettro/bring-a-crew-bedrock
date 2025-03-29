def setup_logging():
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("main.ActionAgent").setLevel(logging.INFO)
    logging.getLogger("main.OrchestrationAgent").setLevel(logging.INFO)