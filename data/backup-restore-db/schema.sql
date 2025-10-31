USE [MangaLibrary]
GO
/****** Object:  Table [dbo].[Chapter]    Script Date: 10/16/2025 7:07:01 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Chapter](
	[ChapterId] [uniqueidentifier] NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[Type] [nvarchar](50) NULL,
	[Volume] [nvarchar](50) NULL,
	[ChapterNumber] [nvarchar](50) NULL,
	[Title] [nvarchar](max) NULL,
	[TranslatedLang] [nvarchar](10) NULL,
	[Pages] [int] NULL,
	[PublishAt] [datetime2](7) NULL,
	[ReadableAt] [datetime2](7) NULL,
	[IsUnavailable] [bit] NULL,
	[CreatedAt] [datetime2](7) NULL,
	[UpdatedAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[ChapterId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Comment]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Comment](
	[CommentId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[ChapterId] [uniqueidentifier] NULL,
	[Content] [nvarchar](max) NULL,
	[CreatedAt] [datetime2](7) NULL,
	[UpdatedAt] [datetime2](7) NULL,
	[IsDeleted] [bit] NULL,
	[IsSpoiler] [bit] NOT NULL,
	[LikeCount] [int] NOT NULL,
	[DislikeCount] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[CommentId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[CommentReaction]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CommentReaction](
	[ReactionId] [uniqueidentifier] NOT NULL,
	[CommentId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[Type] [nvarchar](10) NOT NULL,
	[CreatedAt] [datetime2](7) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[ReactionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Covers]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Covers](
	[cover_id] [uniqueidentifier] NOT NULL,
	[manga_id] [uniqueidentifier] NOT NULL,
	[type] [nvarchar](50) NULL,
	[description] [nvarchar](max) NULL,
	[volume] [nvarchar](50) NULL,
	[fileName] [nvarchar](255) NULL,
	[locale] [nvarchar](10) NULL,
	[createdAt] [datetimeoffset](7) NULL,
	[updatedAt] [datetimeoffset](7) NULL,
	[version] [int] NULL,
	[rel_user_id] [uniqueidentifier] NULL,
	[url] [nvarchar](500) NULL,
	[image_data] [varbinary](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[cover_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Creator]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Creator](
	[CreatorId] [uniqueidentifier] NOT NULL,
	[Type] [nvarchar](50) NULL,
	[Name] [nvarchar](500) NULL,
	[ImageUrl] [nvarchar](max) NULL,
	[BiographyEn] [nvarchar](max) NULL,
	[BiographyJa] [nvarchar](max) NULL,
	[BiographyPtBr] [nvarchar](max) NULL,
	[CreatedAt] [datetime2](7) NULL,
	[UpdatedAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[CreatorId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[CreatorRelationship]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CreatorRelationship](
	[Id] [int] IDENTITY(1,1) NOT NULL,
	[CreatorId] [uniqueidentifier] NOT NULL,
	[RelatedId] [uniqueidentifier] NOT NULL,
	[RelatedType] [nvarchar](50) NULL,
PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[List]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[List](
	[ListId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[Name] [nvarchar](200) NULL,
	[Description] [nvarchar](max) NULL,
	[IsPublic] [bit] NULL,
	[Slug] [nvarchar](255) NULL,
	[Visibility] [nvarchar](20) NOT NULL,
	[CreatedAt] [datetime2](7) NOT NULL,
	[UpdatedAt] [datetime2](7) NOT NULL,
	[FollowerCount] [int] NOT NULL,
	[ItemCount] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[ListId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[ListFollower]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ListFollower](
	[ListId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[FollowedAt] [datetime2](7) NOT NULL,
 CONSTRAINT [PK_ListFollower] PRIMARY KEY CLUSTERED 
(
	[ListId] ASC,
	[UserId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[ListManga]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ListManga](
	[ListId] [uniqueidentifier] NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[AddedAt] [datetime2](7) NULL,
	[Position] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[ListId] ASC,
	[MangaId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Manga]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Manga](
	[MangaId] [uniqueidentifier] NOT NULL,
	[Type] [nvarchar](50) NULL,
	[TitleEn] [nvarchar](500) NULL,
	[ChapterNumbersResetOnNewVolume] [bit] NULL,
	[ContentRating] [nvarchar](50) NULL,
	[CreatedAt] [datetime2](7) NULL,
	[UpdatedAt] [datetime2](7) NULL,
	[IsLocked] [bit] NULL,
	[LastChapter] [nvarchar](50) NULL,
	[LastVolume] [nvarchar](50) NULL,
	[LatestUploadedChapter] [nvarchar](50) NULL,
	[OriginalLanguage] [nvarchar](10) NULL,
	[PublicationDemographic] [nvarchar](50) NULL,
	[State] [nvarchar](50) NULL,
	[Status] [nvarchar](50) NULL,
	[Year] [int] NULL,
	[OfficialLinks] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[MangaId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaAltTitle]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaAltTitle](
	[AltTitleId] [int] IDENTITY(1,1) NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[LangCode] [nvarchar](10) NULL,
	[AltTitle] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[AltTitleId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaAvailableLanguage]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaAvailableLanguage](
	[LangId] [int] IDENTITY(1,1) NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[LangCode] [nvarchar](10) NULL,
PRIMARY KEY CLUSTERED 
(
	[LangId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaCover]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaCover](
	[MangaId] [uniqueidentifier] NOT NULL,
	[CoverId] [uniqueidentifier] NOT NULL,
	[FileName] [nvarchar](255) NOT NULL,
	[DownloadDate] [datetime2](7) NOT NULL,
	[ImageData] [varbinary](max) NOT NULL,
 CONSTRAINT [PK_MangaCover] PRIMARY KEY CLUSTERED 
(
	[MangaId] ASC,
	[CoverId] ASC,
	[FileName] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaCovers]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaCovers](
	[cover_id] [nvarchar](50) NOT NULL,
	[manga_id] [uniqueidentifier] NOT NULL,
	[file_name] [nvarchar](300) NULL,
	[description] [nvarchar](max) NULL,
	[volume] [nvarchar](50) NULL,
	[locale] [nvarchar](20) NULL,
	[created_at] [datetimeoffset](7) NULL,
	[updated_at] [datetimeoffset](7) NULL,
	[version] [int] NULL,
	[image_url] [nvarchar](1000) NULL,
	[file_path] [nvarchar](1000) NULL,
	[downloaded_at] [datetimeoffset](7) NULL,
	[raw_json] [nvarchar](max) NULL,
	[inserted_at] [datetimeoffset](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[cover_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaDescription]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaDescription](
	[DescriptionId] [int] IDENTITY(1,1) NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[LangCode] [nvarchar](10) NULL,
	[Description] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[DescriptionId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaLink]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaLink](
	[LinkId] [int] IDENTITY(1,1) NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[Provider] [nvarchar](20) NULL,
	[Url] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[LinkId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaRelated]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaRelated](
	[MangaId] [uniqueidentifier] NOT NULL,
	[RelatedId] [uniqueidentifier] NOT NULL,
	[Type] [nvarchar](50) NOT NULL,
	[Related] [nvarchar](50) NULL,
	[FetchedAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[MangaId] ASC,
	[RelatedId] ASC,
	[Type] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaStatistics]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaStatistics](
	[StatisticId] [uniqueidentifier] NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[Source] [nvarchar](50) NULL,
	[Follows] [int] NULL,
	[AverageRating] [float] NULL,
	[BayesianRating] [float] NULL,
	[UnavailableChapters] [int] NULL,
	[FetchedAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[StatisticId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MangaTag]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MangaTag](
	[MangaId] [uniqueidentifier] NOT NULL,
	[TagId] [uniqueidentifier] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[MangaId] ASC,
	[TagId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Rating]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Rating](
	[RatingId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[Score] [int] NULL,
PRIMARY KEY CLUSTERED 
(
	[RatingId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[ReadingHistory]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ReadingHistory](
	[HistoryId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[MangaId] [uniqueidentifier] NOT NULL,
	[ChapterId] [uniqueidentifier] NOT NULL,
	[LastPageRead] [int] NULL,
	[ReadAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[HistoryId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Report]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Report](
	[ReportId] [uniqueidentifier] NOT NULL,
	[UserId] [uniqueidentifier] NOT NULL,
	[CommentId] [uniqueidentifier] NOT NULL,
	[Reason] [nvarchar](max) NULL,
	[Status] [nvarchar](50) NULL,
	[CreatedAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[ReportId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Tag]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Tag](
	[TagId] [uniqueidentifier] NOT NULL,
	[GroupName] [nvarchar](100) NULL,
	[NameEn] [nvarchar](200) NULL,
PRIMARY KEY CLUSTERED 
(
	[TagId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[User]    Script Date: 10/16/2025 7:07:02 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[User](
	[UserId] [uniqueidentifier] NOT NULL,
	[Username] [nvarchar](100) NOT NULL,
	[Email] [nvarchar](255) NOT NULL,
	[PasswordHash] [nvarchar](255) NOT NULL,
	[Avatar] [nvarchar](max) NULL,
	[Role] [nvarchar](20) NOT NULL,
	[IsLocked] [bit] NULL,
	[CreatedAt] [datetime2](7) NULL,
PRIMARY KEY CLUSTERED 
(
	[UserId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
ALTER TABLE [dbo].[Comment] ADD  DEFAULT ((0)) FOR [IsSpoiler]
GO
ALTER TABLE [dbo].[Comment] ADD  DEFAULT ((0)) FOR [LikeCount]
GO
ALTER TABLE [dbo].[Comment] ADD  DEFAULT ((0)) FOR [DislikeCount]
GO
ALTER TABLE [dbo].[CommentReaction] ADD  CONSTRAINT [DF_CommentReaction_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[List] ADD  CONSTRAINT [DF_List_FollowerCount]  DEFAULT ((0)) FOR [FollowerCount]
GO
ALTER TABLE [dbo].[List] ADD  CONSTRAINT [DF_List_ItemCount]  DEFAULT ((0)) FOR [ItemCount]
GO
ALTER TABLE [dbo].[ListFollower] ADD  CONSTRAINT [DF_ListFollower_FollowedAt]  DEFAULT (sysutcdatetime()) FOR [FollowedAt]
GO
ALTER TABLE [dbo].[ListManga] ADD  CONSTRAINT [DF_ListManga_Position]  DEFAULT ((0)) FOR [Position]
GO
ALTER TABLE [dbo].[MangaCover] ADD  DEFAULT (getdate()) FOR [DownloadDate]
GO
ALTER TABLE [dbo].[MangaCovers] ADD  DEFAULT (sysutcdatetime()) FOR [inserted_at]
GO
ALTER TABLE [dbo].[Chapter]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[Comment]  WITH CHECK ADD FOREIGN KEY([ChapterId])
REFERENCES [dbo].[Chapter] ([ChapterId])
GO
ALTER TABLE [dbo].[Comment]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[Comment]  WITH CHECK ADD FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
ALTER TABLE [dbo].[CommentReaction]  WITH CHECK ADD  CONSTRAINT [FK_CommentReaction_Comment] FOREIGN KEY([CommentId])
REFERENCES [dbo].[Comment] ([CommentId])
GO
ALTER TABLE [dbo].[CommentReaction] CHECK CONSTRAINT [FK_CommentReaction_Comment]
GO
ALTER TABLE [dbo].[CommentReaction]  WITH CHECK ADD  CONSTRAINT [FK_CommentReaction_User] FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
ALTER TABLE [dbo].[CommentReaction] CHECK CONSTRAINT [FK_CommentReaction_User]
GO
ALTER TABLE [dbo].[CreatorRelationship]  WITH CHECK ADD FOREIGN KEY([CreatorId])
REFERENCES [dbo].[Creator] ([CreatorId])
GO
ALTER TABLE [dbo].[List]  WITH CHECK ADD FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
ALTER TABLE [dbo].[ListFollower]  WITH CHECK ADD  CONSTRAINT [FK_ListFollower_List] FOREIGN KEY([ListId])
REFERENCES [dbo].[List] ([ListId])
GO
ALTER TABLE [dbo].[ListFollower] CHECK CONSTRAINT [FK_ListFollower_List]
GO
ALTER TABLE [dbo].[ListFollower]  WITH CHECK ADD  CONSTRAINT [FK_ListFollower_User] FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
ALTER TABLE [dbo].[ListFollower] CHECK CONSTRAINT [FK_ListFollower_User]
GO
ALTER TABLE [dbo].[ListManga]  WITH CHECK ADD FOREIGN KEY([ListId])
REFERENCES [dbo].[List] ([ListId])
GO
ALTER TABLE [dbo].[ListManga]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaAltTitle]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaAvailableLanguage]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaDescription]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaLink]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaRelated]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaStatistics]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaTag]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[MangaTag]  WITH CHECK ADD FOREIGN KEY([TagId])
REFERENCES [dbo].[Tag] ([TagId])
GO
ALTER TABLE [dbo].[Rating]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[Rating]  WITH CHECK ADD FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
ALTER TABLE [dbo].[ReadingHistory]  WITH CHECK ADD FOREIGN KEY([ChapterId])
REFERENCES [dbo].[Chapter] ([ChapterId])
GO
ALTER TABLE [dbo].[ReadingHistory]  WITH CHECK ADD FOREIGN KEY([MangaId])
REFERENCES [dbo].[Manga] ([MangaId])
GO
ALTER TABLE [dbo].[ReadingHistory]  WITH CHECK ADD FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
ALTER TABLE [dbo].[Report]  WITH CHECK ADD FOREIGN KEY([CommentId])
REFERENCES [dbo].[Comment] ([CommentId])
GO
ALTER TABLE [dbo].[Report]  WITH CHECK ADD FOREIGN KEY([UserId])
REFERENCES [dbo].[User] ([UserId])
GO
