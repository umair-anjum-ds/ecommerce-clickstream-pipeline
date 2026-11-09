"""Create the Spark session used by the whole pipeline."""
import os
import sys

from pyspark.sql import SparkSession

from src import java_env

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_spark(app_name="EcommerceClickstream", shuffle_partitions=8, driver_memory=None):
    """Start (or reuse) a local Spark session.

    * Spark's Python workers must use the same Python as this program.
    * PYTHONPATH lets the workers import our `src` package (needed for the RDD code).
    * ANSI mode is switched off so a division by zero gives NULL instead of crashing the job.
    """
    # set the SPARK_DRIVER_MEMORY environment variable (for example 8g) for big files
    driver_memory = driver_memory or os.environ.get("SPARK_DRIVER_MEMORY", "4g")
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

    java_env.prepare_java()                      # sets JAVA_HOME / PATH when Java is installed but not on the PATH
    try:
        spark = _build_session(app_name, shuffle_partitions, driver_memory)
    except Exception as error:
        if "JAVA_GATEWAY_EXITED" in str(error) or "Java gateway" in str(error):
            raise RuntimeError("Spark could not start Java. Java 17 or newer must be installed and findable.\n"
                               + java_env.INSTALL_HELP) from error
        raise
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def _build_session(app_name, shuffle_partitions, driver_memory):
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.ansi.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")     # avoids network-adapter problems (VPN, Windows)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
