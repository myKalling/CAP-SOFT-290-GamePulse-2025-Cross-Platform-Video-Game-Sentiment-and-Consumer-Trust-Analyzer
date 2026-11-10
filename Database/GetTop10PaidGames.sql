USE [GamePulse]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		Ryan Michael
-- Create date: 11/02/2026
-- Update date: 
-- Description:	Get top 10 paid games
-- EXEC GetTop10PaidGames
-- =============================================
CREATE PROCEDURE dbo.GetTop10PaidGames
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
    SET NOCOUNT ON;

    WITH RankedGames AS (
        SELECT TOP (10)
            g.GameID,
            g.Title,
            g.Price,           
            CAST(AVG(r.Sentiment) AS DECIMAL(5,2))
                AS AverageSentiment
        FROM dbo.Game AS g
        INNER JOIN dbo.Review AS r
            ON g.GameID = r.GameID
        WHERE g.Price > 0
        GROUP BY g.GameID, g.Title, g.Price
        
        ORDER BY
            AVG(r.Sentiment) DESC,
            g.GameID ASC
    )
    SELECT
        rg.GameID,
        rg.Title,
        rg.Price,
        dev.Developers,
        gen.Genres,        
        rg.AverageSentiment
    FROM RankedGames AS rg
    OUTER APPLY (
        SELECT STRING_AGG(
            CONVERT(NVARCHAR(MAX), x.DeveloperName), ', '
        ) AS Developers
        FROM (
            SELECT DISTINCT d.DeveloperName
            FROM dbo.GameDevelopers AS gd
            JOIN dbo.Developer AS d
                ON gd.DeveloperID = d.DeveloperID
            WHERE gd.GameID = rg.GameID
        ) AS x
    ) AS dev
    OUTER APPLY (
        SELECT STRING_AGG(
            CONVERT(NVARCHAR(MAX), x.Genre), ', '
        ) AS Genres
        FROM (
            SELECT DISTINCT ge.Genre
            FROM dbo.GameGenres AS gg
            JOIN dbo.Genre AS ge
                ON gg.GenreID = ge.GenreID
            WHERE gg.GameID = rg.GameID
        ) AS x
    ) AS gen
    ORDER BY
        rg.AverageSentiment DESC,        
        rg.GameID ASC
END;
GO