USE [GamePulse]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		Ryan Michael
-- Create date: 10/26/2026
-- Update date: 
-- Description:	Get Game by ID
-- EXEC GetGame @GameID = 1
-- =============================================
CREATE PROCEDURE [dbo].[GetGame]
	@GameID INT
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	BEGIN TRY
		SELECT 
		GameID,
		Title,
		Price
		FROM dbo.Game
		WHERE GameID = @GameID
	END TRY
	BEGIN CATCH
		SELECT ERROR_MESSAGE() AS ErrorMessage;
	END CATCH
END