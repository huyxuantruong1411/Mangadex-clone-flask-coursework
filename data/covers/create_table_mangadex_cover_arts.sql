CREATE TABLE dbo.MangadexCoverArts (
    cover_id            VARCHAR(50) NOT NULL PRIMARY KEY, -- từ data.id
    
    -- Top-level
    result              VARCHAR(20) NULL,
    response            VARCHAR(20) NULL,
    fetched_at          DATETIME2 NULL,

    -- data.attributes
    description         NVARCHAR(MAX) NULL,
    volume              VARCHAR(20) NULL,
    file_name           VARCHAR(255) NULL,
    locale              VARCHAR(10) NULL,
    created_at          DATETIME2 NULL,
    updated_at          DATETIME2 NULL,
    version             INT NULL,

    -- relationships (giữ 2 loại phổ biến)
    manga_id            VARCHAR(50) NULL,
    user_id             VARCHAR(50) NULL
);
