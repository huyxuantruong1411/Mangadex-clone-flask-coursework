IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'MangaLibrary')
BEGIN
    CREATE DATABASE MangaLibrary;
    PRINT 'Database MangaLibrary created.';
END
GO

RESTORE DATABASE MangaLibrary
FROM DISK = '/var/opt/mssql/backup/MangaLibrary.bak'
WITH MOVE 'MangaLibrary' TO '/var/opt/mssql/data/MangaLibrary.mdf',
     MOVE 'MangaLibrary_log' TO '/var/opt/mssql/data/MangaLibrary_log.ldf',
     REPLACE;
GO

PRINT 'Restore MangaLibrary completed!';