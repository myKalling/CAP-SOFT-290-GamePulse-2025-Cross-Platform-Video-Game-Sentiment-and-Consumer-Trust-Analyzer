USE [GamePulse]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		Ryan Michael
-- Create date: 11/03/2026
-- Update date: 
-- Description:	Procedure for a search bar on the website to use to find a game title
-- EXEC SearchGames @SearchTerm = "frag"
-- =============================================
CREATE PROCEDURE SearchGames
    @SearchTerm NVARCHAR(100) = NULL
AS
BEGIN
    -- Protect against empty or NULL inputs by defaulting to an empty string if null
    SET @SearchTerm = ISNULL(@SearchTerm, '');

    -- Execute the search query
    SELECT TOP 50
            g.GameID,
            g.Title,
            g.Price,
            COUNT(r.ReviewID) AS ReviewCount,
            CAST(AVG(r.Sentiment) AS DECIMAL(5,2))
                AS AverageSentiment

        FROM dbo.Game g
        LEFT JOIN dbo.Review r
            ON g.GameID = r.GameID

        WHERE g.Title LIKE '%' + @SearchTerm + '%'

        GROUP BY
            g.GameID,
            g.Title,
            g.Price

        ORDER BY
            CASE
                WHEN g.Title = @SearchTerm THEN 0
                WHEN g.Title LIKE @SearchTerm + '%' THEN 1
                ELSE 2
            END,
            g.Title ASC
END;