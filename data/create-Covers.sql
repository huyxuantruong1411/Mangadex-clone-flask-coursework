USE MangaLibrary;
GO

IF OBJECT_ID('dbo.Covers', 'U') IS NOT NULL
    DROP TABLE dbo.Covers;
GO

CREATE TABLE dbo.Covers (
    cover_id UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    manga_id UNIQUEIDENTIFIER NOT NULL,
    type NVARCHAR(50) NULL,
    description NVARCHAR(MAX) NULL,
    volume NVARCHAR(50) NULL,
    fileName NVARCHAR(255) NULL,
    locale NVARCHAR(10) NULL,
    createdAt DATETIMEOFFSET NULL,
    updatedAt DATETIMEOFFSET NULL,
    version INT NULL,
    rel_user_id UNIQUEIDENTIFIER NULL,
    url NVARCHAR(500) NULL,
    image_data VARBINARY(MAX) NULL
);
GO
