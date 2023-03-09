import os
import argparse
import time
import mlflow

import random
import string
from pyspark.context import SparkContext
from pyspark.sql.session import SparkSession
from pyspark import SparkConf, SparkContext
import pandas as pd

conf = SparkConf().setAppName("appName").setMaster("local")
sc = SparkContext.getOrCreate(conf=conf)
spark = SparkSession(sc)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_csv", type=str, help="data_csv")
    args = parser.parse_args()

    data_csv = args.data_csv

    print("data_csv: {}".format(data_csv))

    df = spark.read.csv(data_csv+'/*.csv', header=True, inferSchema=True)
    # change groupID to float
    df = df.withColumn("groupID", df["groupID"].cast("float"))
    # change average to float
    df = df.withColumn("average", df["average"].cast("float"))
    # Reduce by groupID and calculate the average and total and keep the other columns
    df = df.groupBy('groupID').agg({'system_prod':'first', 'processor_prod':'first', 'cpu_brand_prod':'first', 'cpu_hz_prod':'first', 'cpu_cores_prod':'first', 'cpu_cores_total_prod':'first', 'ram_total_prod':'first', 'pricePerHour_prod':'first', 'system_cons':'first', 'processor_cons':'first', 'cpu_brand_cons':'first', 'cpu_hz_cons':'first', 'cpu_cores_cons':'first', 'cpu_cores_total_cons':'first', 'ram_total_cons':'first', 'pricePerHour_cons':'first', 'average':'avg', 'total':'sum', 'flow':'first', 'batch_size':'first', 'machine_kafka':'first'})
    # transform the dataframe to a pandas dataframe
    # Remove first/avg/sum and () from the column names
    df = df.toPandas()
    df.columns = df.columns.str.replace('first', '')
    df.columns = df.columns.str.replace('avg', '')
    df.columns = df.columns.str.replace('sum', '')
    df.columns = df.columns.str.replace('(', '')
    df.columns = df.columns.str.replace(')', '')
    # order the columns by groupID
    df = df[['groupID', 'system_prod', 'processor_prod', 'cpu_brand_prod', 'cpu_hz_prod', 'cpu_cores_prod', 'cpu_cores_total_prod', 'ram_total_prod', 'pricePerHour_prod', 'system_cons', 'processor_cons', 'cpu_brand_cons', 'cpu_hz_cons', 'cpu_cores_cons', 'cpu_cores_total_cons', 'ram_total_cons', 'pricePerHour_cons', 'machine_kafka', 'total', 'average', 'batch_size', 'flow']]
    

    # Order the dataframe by groupID
    df = df.sort_values(by=['groupID'])

    
    # write the pandas dataframe to a csv file
    df.to_csv('cleaned.csv', index=False)

    # Upload the file to the mlflow
    mlflow.log_artifact('cleaned.csv')

if __name__ == "__main__":
    main()
