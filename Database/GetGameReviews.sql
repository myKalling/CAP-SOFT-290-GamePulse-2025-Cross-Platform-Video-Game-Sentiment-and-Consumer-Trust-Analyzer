USE [GamePulse]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		Ryan Michael
-- Create date: 11/01/2026
-- Update date: 
-- Description:	Get Reviews by Game ID
-- EXEC GetGameReviews @GameID = 1
-- =============================================
CREATE PROCEDURE [dbo].[GetGameReviews]
	@GameID INT
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	BEGIN TRY
		SELECT 
		g.GameID,
		Title,
		r.Review,
		r.Sentiment,
		r.ReviewDate,
		r.UserID
		FROM dbo.Game as g
		JOIN dbo.Review as r
		ON g.GameID = r.GameID
		WHERE g.GameID = @GameID
	END TRY
	BEGIN CATCH
		SELECT ERROR_MESSAGE() AS ErrorMessage;
	END CATCH
END