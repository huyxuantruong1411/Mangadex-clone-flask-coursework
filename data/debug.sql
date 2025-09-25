SELECT TOP (1000) [MangaId]
      ,[Type]
      ,[TitleEn]
      ,[ChapterNumbersResetOnNewVolume]
      ,[ContentRating]
      ,[CreatedAt]
      ,[UpdatedAt]
      ,[IsLocked]
      ,[LastChapter]
      ,[LastVolume]
      ,[LatestUploadedChapter]
      ,[OriginalLanguage]
      ,[PublicationDemographic]
      ,[State]
      ,[Status]
      ,[Year]
      ,[OfficialLinks]
  FROM [MangaLibrary].[dbo].[Manga];


SELECT 
	Manga.MangaId,
	Manga.ContentRating,
	Tag.*
  FROM [MangaLibrary].[dbo].[Manga]
  join MangaLibrary.dbo.MangaTag on Manga.MangaId = MangaTag.MangaId
  join MangaLibrary.dbo.Tag on Tag.TagId = MangaTag.TagId
  where tag.GroupName = 'content'
  order by MangaId

  select 
  Manga.MangaId,
  MangaDescription.LangCode,
  MangaDescription.[Description]
  from [MangaLibrary].[dbo].[Manga]
  join [MangaLibrary].[dbo].MangaDescription on Manga.MangaId = MangaDescription.MangaId
  where MangaDescription.LangCode in ('en', 'vi', 'ja')


  select
	Manga.MangaId,
	MangaStatistics.StatisticId,
	MangaStatistics.Follows,
	MangaStatistics.AverageRating,
	MangaStatistics.BayesianRating
  from [MangaLibrary].[dbo].Manga
  join [MangaLibrary].[dbo].[MangaStatistics] on Manga.MangaId = MangaStatistics.MangaId
  order by Manga.MangaId

    select 
  Manga.MangaId,
  MangaRelated.RelatedId,
  MangaRelated.[Type],
  Creator.*
  from [MangaLibrary].[dbo].[Manga]
  join [MangaLibrary].[dbo].MangaRelated on Manga.MangaId = MangaRelated.MangaId
  join [MangaLibrary].[dbo].Creator on MangaRelated.RelatedId = Creator.CreatorId
  where MangaRelated.[Type] in ('artist', 'author')
  order by Manga.MangaId

  select
	Manga.MangaId,
	Manga.PublicationDemographic,
	Tag.*
  from [MangaLibrary].[dbo].[Manga]
  join [MangaLibrary].[dbo].MangaTag on Manga.MangaId = MangaTag.MangaId
  join [MangaLibrary].[dbo].Tag on MangaTag.TagId = Tag.TagId
  where Tag.GroupName in ('genre', 'theme', 'format')
  order by Manga.MangaId,tag.GroupName

  select
	Manga.MangaId,
	MangaLink.[Provider],
	MangaLink.[Url]
  from [MangaLibrary].[dbo].[Manga]
  join [MangaLibrary].[dbo].MangaLink on Manga.MangaId = MangaLink.MangaId

    select
	Manga.MangaId,
	MangaAltTitle.LangCode,
	MangaAltTitle.AltTitle
	from [MangaLibrary].[dbo].[Manga]
	join [MangaLibrary].[dbo].MangaAltTitle on Manga.MangaId = MangaAltTitle.MangaId

	select distinct LangCode
	from [MangaLibrary].[dbo].MangaAltTitle


select
	Manga.MangaId,
	Manga.TitleEn,
	MangaAltTitle.AltTitle,
	MangaAltTitle.LangCode
from [MangaLibrary].[dbo].[Manga]
join [MangaLibrary].[dbo].MangaAltTitle on Manga.MangaId = MangaAltTitle.MangaId


SELECT 
Creator.CreatorId,
Creator.[Name],
Creator.BiographyEn,
Manga.MangaId,
Manga.TitleEn,
MangaStatistics.AverageRating,
MangaStatistics.BayesianRating,
MangaStatistics.Follows
  FROM [MangaLibrary].[dbo].Creator
join  [MangaLibrary].[dbo].[CreatorRelationship] on Creator.CreatorId = CreatorRelationship.CreatorId
  join [MangaLibrary].[dbo].Manga on CreatorRelationship.RelatedId = Manga.MangaId
  join [MangaLibrary].[dbo].MangaStatistics on Manga.MangaId = MangaStatistics.MangaId
  order by Creator.CreatorId

-------------------

USE [MangaLibrary]
GO

INSERT INTO [dbo].[User] (
    UserId,
    Username,
    Email,
    PasswordHash,
    Role,
    IsLocked,
    CreatedAt
)
VALUES (
    NEWID(),                           -- Tạo GUID mới cho UserId
    'admin',                            -- Username
    'admin@example.com',                -- Email
    HASHBYTES('SHA2_256', 'Admin@123'), -- Password hash (hoặc dùng hash đã tạo sẵn từ app)
    'Admin',                            -- Role
    0,                                  -- IsLocked = false
    GETDATE()                           -- CreatedAt = hiện tại
);
GO
