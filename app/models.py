from datetime import datetime
import uuid
from flask_login import UserMixin
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy import Column, LargeBinary, PrimaryKeyConstraint, String, Integer, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from . import db

# ------------------------
# USER
# ------------------------
class User(UserMixin, db.Model):
    __tablename__ = "User"
    __table_args__ = {"schema": "dbo"}

    UserId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    Username = Column(String(100), nullable=False)
    Email = Column(String(255), nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    Avatar = Column(Text)
    Role = Column(String(20), nullable=False)
    IsLocked = Column(Boolean)
    CreatedAt = Column(DateTime, default=datetime.utcnow)

    # relationships
    comments = relationship("Comment", back_populates="user")
    ratings = relationship("Rating", back_populates="user")
    lists = relationship("List", back_populates="user")
    histories = relationship("ReadingHistory", back_populates="user")
    reports = relationship("Report", back_populates="user")

    def get_id(self):
        return str(self.UserId)

# ------------------------
# MANGA
# ------------------------
class Manga(db.Model):
    __tablename__ = "Manga"
    __table_args__ = {"schema": "dbo"}

    MangaId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    Type = Column(String(50))
    TitleEn = Column(String(500))
    ChapterNumbersResetOnNewVolume = Column(Boolean)
    ContentRating = Column(String(50))
    CreatedAt = Column(DateTime)
    UpdatedAt = Column(DateTime)
    IsLocked = Column(Boolean)
    LastChapter = Column(String(50))
    LastVolume = Column(String(50))
    LatestUploadedChapter = Column(String(50))
    OriginalLanguage = Column(String(10))
    PublicationDemographic = Column(String(50))
    State = Column(String(50))
    Status = Column(String(50))
    Year = Column(Integer)
    OfficialLinks = Column(Text)

    # relationships
    chapters = relationship("Chapter", back_populates="manga")
    comments = relationship("Comment", back_populates="manga")
    ratings = relationship("Rating", back_populates="manga")
    alt_titles = relationship("MangaAltTitle", back_populates="manga")
    descriptions = relationship("MangaDescription", back_populates="manga")
    links = relationship("MangaLink", back_populates="manga")
    stats = relationship("MangaStatistics", back_populates="manga")
    available_languages = relationship("MangaAvailableLanguage", back_populates="manga")
    tags = relationship("MangaTag", back_populates="manga")
    histories = relationship("ReadingHistory", back_populates="manga")


# ------------------------
# CHAPTER
# ------------------------
class Chapter(db.Model):
    __tablename__ = "Chapter"
    __table_args__ = {"schema": "dbo"}

    ChapterId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    Type = Column(String(50))
    Volume = Column(String(50))
    ChapterNumber = Column(String(50))
    Title = Column(Text)
    TranslatedLang = Column(String(10))
    Pages = Column(Integer)
    PublishAt = Column(DateTime)
    ReadableAt = Column(DateTime)
    IsUnavailable = Column(Boolean)
    CreatedAt = Column(DateTime)
    UpdatedAt = Column(DateTime)

    manga = relationship("Manga", back_populates="chapters")
    comments = relationship("Comment", back_populates="chapter")
    histories = relationship("ReadingHistory", back_populates="chapter")


# ------------------------
# COMMENT
# ------------------------
class Comment(db.Model):
    __tablename__ = 'Comment'
    __table_args__ = {'schema': 'dbo'}
    CommentId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    UserId = db.Column(db.String(36), db.ForeignKey('dbo.User.UserId'), nullable=False)
    MangaId = db.Column(db.String(36), db.ForeignKey('dbo.Manga.MangaId'), nullable=False)
    ChapterId = db.Column(db.String(36), db.ForeignKey('dbo.Chapter.ChapterId'), nullable=True)
    Content = db.Column(db.Text, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    IsDeleted = db.Column(db.Boolean, default=False)
    IsSpoiler = db.Column(db.Boolean, default=False)
    LikeCount = db.Column(db.Integer, default=0)
    DislikeCount = db.Column(db.Integer, default=0)

    user = relationship("User", back_populates="comments")
    manga = relationship("Manga", back_populates="comments")
    chapter = relationship("Chapter", back_populates="comments")
    reports = relationship("Report", back_populates="comment")


# ------------------------
# CREATOR
# ------------------------
class Creator(db.Model):
    __tablename__ = "Creator"
    __table_args__ = {"schema": "dbo"}

    CreatorId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    Type = Column(String(50))
    Name = Column(String(500))
    ImageUrl = Column(Text)
    BiographyEn = Column(Text)
    BiographyJa = Column(Text)
    BiographyPtBr = Column(Text)
    CreatedAt = Column(DateTime)
    UpdatedAt = Column(DateTime)

    relationships = relationship("CreatorRelationship", back_populates="creator")


class CreatorRelationship(db.Model):
    __tablename__ = "CreatorRelationship"
    __table_args__ = {"schema": "dbo"}

    Id = Column(Integer, primary_key=True, autoincrement=True)
    CreatorId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Creator.CreatorId"))
    RelatedId = Column(UNIQUEIDENTIFIER, nullable=False)
    RelatedType = Column(String(50))

    creator = relationship("Creator", back_populates="relationships")


# ------------------------
# LIST
# ------------------------
class List(db.Model):
    __tablename__ = "List"
    __table_args__ = {"schema": "dbo"}

    ListId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    UserId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.User.UserId"))
    Name = Column(String(200))
    Description = Column(Text)
    IsPublic = Column(Boolean)

    Slug = Column(String(20))
    Visibility = Column(String(20))
    CreatedAt = Column(DateTime)
    UpdatedAt = Column(DateTime)

    FollowerCount = Column(Integer, default=0)
    ItemCount = Column(Integer, default=0)
    # relationships

    user = relationship("User", back_populates="lists")
    mangas = relationship("ListManga", back_populates="list")
    followers = relationship("ListFollower", back_populates="list")


class ListManga(db.Model):
    __tablename__ = "ListManga"
    __table_args__ = {"schema": "dbo"}

    ListId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.List.ListId"), primary_key=True)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"), primary_key=True)
    AddedAt = Column(DateTime)
    Position = Column(Integer, default=0)

    list = relationship("List", back_populates="mangas")
    manga = relationship("Manga")

class ListFollower(db.Model):
    __tablename__ = "ListFollower"
    __table_args__ = {"schema": "dbo"}

    ListId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.List.ListId"), primary_key=True)
    UserId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.User.UserId"), primary_key=True)
    FollowedAt = Column(DateTime, default=datetime.utcnow)

    list = relationship("List", back_populates="followers")
    user = relationship("User")

# ------------------------
# MANGA RELATED TABLES
# ------------------------
class MangaAltTitle(db.Model):
    __tablename__ = "MangaAltTitle"
    __table_args__ = {"schema": "dbo"}

    AltTitleId = Column(Integer, primary_key=True, autoincrement=True)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    LangCode = Column(String(10))
    AltTitle = Column(Text)

    manga = relationship("Manga", back_populates="alt_titles")


class MangaAvailableLanguage(db.Model):
    __tablename__ = "MangaAvailableLanguage"
    __table_args__ = {"schema": "dbo"}

    LangId = Column(Integer, primary_key=True, autoincrement=True)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    LangCode = Column(String(10))

    manga = relationship("Manga", back_populates="available_languages")


class MangaDescription(db.Model):
    __tablename__ = "MangaDescription"
    __table_args__ = {"schema": "dbo"}

    DescriptionId = Column(Integer, primary_key=True, autoincrement=True)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    LangCode = Column(String(10))
    Description = Column(Text)

    manga = relationship("Manga", back_populates="descriptions")


class MangaLink(db.Model):
    __tablename__ = "MangaLink"
    __table_args__ = {"schema": "dbo"}

    LinkId = Column(Integer, primary_key=True, autoincrement=True)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    Provider = Column(String(20))
    Url = Column(Text)

    manga = relationship("Manga", back_populates="links")


class MangaRelated(db.Model):
    __tablename__ = "MangaRelated"
    __table_args__ = {"schema": "dbo"}

    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"), primary_key=True)
    RelatedId = Column(UNIQUEIDENTIFIER, primary_key=True)
    Type = Column(String(50), primary_key=True)
    Related = Column(String(50))
    FetchedAt = Column(DateTime)


class MangaStatistics(db.Model):
    __tablename__ = "MangaStatistics"
    __table_args__ = {"schema": "dbo"}

    StatisticId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    Source = Column(String(50))
    Follows = Column(Integer)
    AverageRating = Column(Float)
    BayesianRating = Column(Float)
    UnavailableChapters = Column(Integer)
    FetchedAt = Column(DateTime)

    manga = relationship("Manga", back_populates="stats")


class Tag(db.Model):
    __tablename__ = "Tag"
    __table_args__ = {"schema": "dbo"}

    TagId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    GroupName = Column(String(100))
    NameEn = Column(String(200))

    mangas = relationship("MangaTag", back_populates="tag")


class MangaTag(db.Model):
    __tablename__ = "MangaTag"
    __table_args__ = {"schema": "dbo"}

    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"), primary_key=True)
    TagId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Tag.TagId"), primary_key=True)

    manga = relationship("Manga", back_populates="tags")
    tag = relationship("Tag", back_populates="mangas")


# ------------------------
# RATING, HISTORY, REPORT
# ------------------------
class Rating(db.Model):
    __tablename__ = "Rating"
    __table_args__ = {"schema": "dbo"}

    RatingId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    UserId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.User.UserId"))
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    Score = Column(Integer)

    user = relationship("User", back_populates="ratings")
    manga = relationship("Manga", back_populates="ratings")


class ReadingHistory(db.Model):
    __tablename__ = "ReadingHistory"
    __table_args__ = {"schema": "dbo"}

    HistoryId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    UserId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.User.UserId"))
    MangaId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Manga.MangaId"))
    ChapterId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Chapter.ChapterId"))
    LastPageRead = Column(Integer)
    ReadAt = Column(DateTime)

    user = relationship("User", back_populates="histories")
    manga = relationship("Manga", back_populates="histories")
    chapter = relationship("Chapter", back_populates="histories")


class Report(db.Model):
    __tablename__ = "Report"
    __table_args__ = {"schema": "dbo"}

    ReportId = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    UserId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.User.UserId"))
    CommentId = Column(UNIQUEIDENTIFIER, ForeignKey("dbo.Comment.CommentId"))
    Reason = Column(Text)
    Status = Column(String(50))
    CreatedAt = Column(DateTime)

    user = relationship("User", back_populates="reports")
    comment = relationship("Comment", back_populates="reports")
    
# ------------------------
# MANGA COVER
# ------------------------
class MangaCover(db.Model):
    __tablename__ = "MangaCover"
    __table_args__ = (
        PrimaryKeyConstraint("MangaId", "CoverId", "FileName", name="PK_MangaCover"),
        {"schema": "dbo"}
    )

    MangaId = Column(UNIQUEIDENTIFIER, nullable=False)
    CoverId = Column(UNIQUEIDENTIFIER, nullable=False)
    FileName = Column(String(255), nullable=False)
    DownloadDate = Column(DateTime, nullable=False, default=datetime.utcnow)
    ImageData = Column(LargeBinary, nullable=False)


class Cover(db.Model):
    __tablename__ = "Covers"

    cover_id = db.Column(db.String(36), primary_key=True)  # UUID string
    manga_id = db.Column(db.String(36), nullable=False)
    type = db.Column(db.String(50))
    description = db.Column(db.Text)
    volume = db.Column(db.String(50))
    fileName = db.Column(db.String(255))
    locale = db.Column(db.String(10))
    createdAt = db.Column(db.DateTime)
    updatedAt = db.Column(db.DateTime)
    version = db.Column(db.Integer)
    rel_user_id = db.Column(db.String(36))
    url = db.Column(db.String(500))
    image_data = db.Column(db.LargeBinary)  # lưu binary ảnh