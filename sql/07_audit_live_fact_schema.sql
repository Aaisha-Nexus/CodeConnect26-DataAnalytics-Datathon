USE NexusMartDW;
GO

SELECT
    c.column_id,
    c.name AS ColumnName,
    TYPE_NAME(c.user_type_id) AS DataType,
    c.max_length,
    c.is_nullable
FROM sys.columns AS c
WHERE c.object_id = OBJECT_ID('dw.FactSales')
ORDER BY c.column_id;
GO

SELECT COUNT_BIG(*) AS ExistingFactRows
FROM dw.FactSales;
GO


USE NexusMartDW;
GO

-- 1. Show every FactSales column in one row
SELECT STRING_AGG(CAST(name AS VARCHAR(MAX)), ', ')
       WITHIN GROUP (ORDER BY column_id) AS FactSalesColumns
FROM sys.columns
WHERE object_id = OBJECT_ID('dw.FactSales');
GO

-- 2. Show primary key, unique constraints and foreign keys
SELECT
    i.name AS ConstraintOrIndexName,
    i.type_desc AS IndexType,
    i.is_primary_key,
    i.is_unique,
    COL_NAME(ic.object_id, ic.column_id) AS ColumnName
FROM sys.indexes i
JOIN sys.index_columns ic
    ON i.object_id = ic.object_id
   AND i.index_id = ic.index_id
WHERE i.object_id = OBJECT_ID('dw.FactSales')
  AND i.is_hypothetical = 0
ORDER BY i.name, ic.key_ordinal;
GO

SELECT
    fk.name AS ForeignKeyName,
    OBJECT_NAME(fk.referenced_object_id) AS ReferencedTable
FROM sys.foreign_keys fk
WHERE fk.parent_object_id = OBJECT_ID('dw.FactSales');
GO
