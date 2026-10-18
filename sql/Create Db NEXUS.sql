IF DB_ID('NexusMartDW') IS NULL
BEGIN
    CREATE DATABASE NexusMartDW;
END;
GO

SELECT name
FROM sys.databases
WHERE name = 'NexusMartDW';
GO