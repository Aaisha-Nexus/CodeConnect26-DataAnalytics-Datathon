
USE NexusMartDW;
GO

-- 1. Check DateKey identity and nullability before inserting.
SELECT
    c.name AS ColumnName,
    TYPE_NAME(c.user_type_id) AS DataType,
    c.is_identity AS IsIdentity,
    c.is_nullable AS IsNullable
FROM sys.columns c
WHERE c.object_id = OBJECT_ID('dw.DimDate')
  AND c.name IN ('DateKey', 'FullDate');
GO

-- 2. Check whether the Unknown date row already exists.
SELECT *
FROM dw.DimDate
WHERE DateKey = 0;
GO

-- 3. Check current foreign-key relationships.
SELECT
    OBJECT_NAME(fk.parent_object_id) AS FromTable,
    COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS FromColumn,
    OBJECT_NAME(fk.referenced_object_id) AS ToTable,
    COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ToColumn
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc
    ON fk.object_id = fkc.constraint_object_id
ORDER BY FromTable, ToTable;
GO
