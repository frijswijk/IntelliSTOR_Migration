rem set Migration_data=D:\_IntelliSTOR_Migration\Migration_data
set Migration_data=C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\Migration_data
set SQLServer=localhost
set SQL-SG-Database=iSTSGUAT
set SQL-MY-Database=iSTMYUAT
rem -- user output
set Users-MY=%Migration_data%\Users_MY
set Users-SG=%Migration_data%\Users_SG
set Users-Test=%Migration_data%\Users_Test
rem --report species and folders
set ReportSpecies_SG=%Migration_data%\ReportSpecies_SG
set ReportSpecies_MY=%Migration_data%\ReportSpecies_MY

rem -- Instances extraction
set Instances_Input_SG=%ReportSpecies_SG%\Report_Species.csv
set Instances_Input_MY=%ReportSpecies_MY%\Report_Species.csv
set Instances_Output_SG=%Migration_data%\Instances_SG
set Instances_Output_MY=%Migration_data%\Instances_MY
set Instances_StartYear_SG=2020
set Instances_StartYear_MY=1900

rem -- Test File Generation
set TestGen_ReportSpecies_SG=%ReportSpecies_SG%\Report_Species.csv
set TestGen_ReportSpecies_MY=%ReportSpecies_MY%\Report_Species.csv
set TestGen_FolderExtract_SG=%Instances_Output_SG%
set TestGen_FolderExtract_MY=%Instances_Output_MY%
set TestGen_TargetFolder_SG=%Migration_data%\TestFiles_SG
set TestGen_TargetFolder_MY=%Migration_data%\TestFiles_MY
set TestGen_MaxSpecies=5

rem -- Zip and Encrypt
set ZipEncrypt_SourceFolder_SG=%TestGen_TargetFolder_SG%
set ZipEncrypt_SourceFolder_MY=%TestGen_TargetFolder_MY%
set ZipEncrypt_OutputFolder_SG=%Migration_data%\EncryptedArchives_SG
set ZipEncrypt_OutputFolder_MY=%Migration_data%\EncryptedArchives_MY
set ZipEncrypt_SpeciesCSV_SG=%ReportSpecies_SG%\Report_Species.csv
set ZipEncrypt_SpeciesCSV_MY=%ReportSpecies_MY%\Report_Species.csv
set ZipEncrypt_InstancesFolder_SG=%Instances_Output_SG%
set ZipEncrypt_InstancesFolder_MY=%Instances_Output_MY%
set ZipEncrypt_Password=YourSecurePassword123
set ZipEncrypt_CompressionLevel=5
set ZipEncrypt_MaxSpecies=5
set ZipEncrypt_DeleteAfterCompress=No
rem set ZipEncrypt_7zipPath=C:\Program Files\7-Zip\7z.exe

rem -- AFP Resources
set AFP_Source_SG=C:\Users\freddievr\Downloads\afp\afp
set AFP_Source_MY=C:\Users\freddievr\Downloads\afp\afp
set AFP_Output=%Migration_data%\AFP_Resources
set AFP_VersionCompare=Yes
rem Set AFP_VersionCompare=Yes to enable binary content comparison (removes duplicate versions)
rem Set AFP_VersionCompare=No to list all versions regardless of content
set AFP_FromYear=
rem Set AFP_FromYear to a year (e.g., 2020) to ignore resources before that year. Leave empty to include all years.
set AFP_AllNameSpaces=No
rem Set AFP_AllNameSpaces=Yes to combine resources from all namespaces into a single list (requires AFP_VersionCompare=Yes)
rem Set AFP_AllNameSpaces=No to keep namespaces separate (default)

rem -- AFP Resources Export
set AFP_Export_SG=%Migration_data%\AFP_Export_SG
set AFP_Export_MY=%Migration_data%\AFP_Export_MY

rem -- LDAP Integration
set LDAP_Server=YLDAPTEST-DC01.ldap1test.loc
set LDAP_Port=636
set LDAP_SSL=--use-ssl --ssl-no-verify
set LDAP_BindDN=cn=administrator,cn=Users,dc=ldap1test,dc=loc
set LDAP_Password=Linked3-Shorten-Crestless
set LDAP_BaseDN=dc=ldap1test,dc=loc
set LDAP_GroupsOU=ou=Groups,dc=ldap1test,dc=loc
set LDAP_UsersOU=ou=Users,dc=ldap1test,dc=loc
set LDAP_PasswordStrategy=skip
set LDAP_TestUserCount=10
rem Set LDAP_TestUserCount to 1, 5, 10, 100, or "all"
set LDAP_PreparedDir=%Migration_data%\LDAP_Import
set LDAP_TranslatedDir=%Migration_data%\LDAP_Translated_Permissions
set LDAP_RidMapping=%Migration_data%\LDAP_Import\rid_mapping.csv

