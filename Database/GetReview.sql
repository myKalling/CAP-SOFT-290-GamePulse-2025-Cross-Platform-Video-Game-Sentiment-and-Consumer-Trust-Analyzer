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
-- Description:	Get Review by ID
-- EXEC GetReview @ReviewID = 1
-- =============================================
CREATE PROCEDURE [dbo].[GetReview]
	@ReviewID INT
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	BEGIN TRY
		SELECT 
		ReviewID,
		g.Title,
		Review,
		Sentiment,
		ReviewDate,
		UserID
		FROM dbo.Review as r
		JOIN dbo.Game as g
		ON g.GameID = r.GameID
		WHERE ReviewID = @ReviewID
	END TRY
	BEGIN CATCH
		SELECT ERROR_MESSAGE() AS ErrorMessage;
	END CATCH
END