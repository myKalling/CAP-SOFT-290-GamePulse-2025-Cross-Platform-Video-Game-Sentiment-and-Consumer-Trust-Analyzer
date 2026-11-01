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
-- Description:	Get all Developers
-- EXEC GetAllDevelopers
-- =============================================
CREATE PROCEDURE [dbo].[GetAllDevelopers]
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	BEGIN TRY
		SELECT 
		DeveloperID,
		DeveloperName
		FROM dbo.Developer
	END TRY
	BEGIN CATCH
		SELECT ERROR_MESSAGE() AS ErrorMessage;
	END CATCH
END