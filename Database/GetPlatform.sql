USE [GamePulse]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		Ryan Michael
-- Create date: 10/21/2026
-- Update date: 
-- Description:	Get Platform by ID
-- EXEC GetPlatform @PlatformID = 1
-- =============================================
CREATE PROCEDURE [dbo].[GetPlatform]
	@PlatformID INT
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	BEGIN TRY
		SELECT 
		PlatformID,
		PlatformName
		FROM dbo.[Platform]
		WHERE PlatformID = @PlatformID
	END TRY
	BEGIN CATCH
		SELECT ERROR_MESSAGE() AS ErrorMessage;
	END CATCH
END