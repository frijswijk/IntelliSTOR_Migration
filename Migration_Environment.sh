#!/bin/bash
# Migration Environment Variables for macOS
# Source this file in other scripts: source ../Migration_Environment.sh

# Base paths - adjust to your macOS environment
#
export Migration_data="/Volumes/acasis/projects/python/ocbc/Migration_Data"

export SQLServer="localhost"
export SQLUser="sa"
export SQLPassword="Fvrpgr40"
export SQL_SG_Database="iSTSGUAT"
export SQL_MY_Database="iSTMYUAT"

# User output
export Users_MY="${Migration_data}/Users_MY"
export Users_SG="${Migration_data}/Users_SG"
export Users_Test="${Migration_data}/Users_Test"

# Report species and folders
export ReportSpecies_SG="${Migration_data}/ReportSpecies_SG"
export ReportSpecies_MY="${Migration_data}/ReportSpecies_MY"

# Instances extraction
export Instances_Input_SG="${ReportSpecies_SG}/Report_Species.csv"
export Instances_Input_MY="${ReportSpecies_MY}/Report_Species.csv"
export Instances_Output_SG="${Migration_data}/Instances_SG"
export Instances_Output_MY="${Migration_data}/Instances_MY"
export Instances_StartYear_SG="2020"
export Instances_StartYear_MY="1900"

# Test File Generation
export TestGen_ReportSpecies_SG="${ReportSpecies_SG}/Report_Species.csv"
export TestGen_ReportSpecies_MY="${ReportSpecies_MY}/Report_Species.csv"
export TestGen_FolderExtract_SG="${Instances_Output_SG}"
export TestGen_FolderExtract_MY="${Instances_Output_MY}"
export TestGen_TargetFolder_SG="${Migration_data}/TestFiles_SG"
export TestGen_TargetFolder_MY="${Migration_data}/TestFiles_MY"
export TestGen_MaxSpecies="5"

# Zip and Encrypt
export ZipEncrypt_SourceFolder_SG="${TestGen_TargetFolder_SG}"
export ZipEncrypt_SourceFolder_MY="${TestGen_TargetFolder_MY}"
export ZipEncrypt_OutputFolder_SG="${Migration_data}/EncryptedArchives_SG"
export ZipEncrypt_OutputFolder_MY="${Migration_data}/EncryptedArchives_MY"
export ZipEncrypt_SpeciesCSV_SG="${ReportSpecies_SG}/Report_Species.csv"
export ZipEncrypt_SpeciesCSV_MY="${ReportSpecies_MY}/Report_Species.csv"
export ZipEncrypt_InstancesFolder_SG="${Instances_Output_SG}"
export ZipEncrypt_InstancesFolder_MY="${Instances_Output_MY}"
export ZipEncrypt_Password="YourSecurePassword123"
export ZipEncrypt_CompressionLevel="5"
export ZipEncrypt_MaxSpecies="5"
export ZipEncrypt_DeleteAfterCompress="No"

# AFP Resources
export AFP_Source_SG="$HOME/Downloads/afp/afp"
export AFP_Source_MY="$HOME/Downloads/afp/afp"
export AFP_Output="${Migration_data}/AFP_Resources"
export AFP_VersionCompare="Yes"
# Set AFP_VersionCompare=Yes to enable binary content comparison (removes duplicate versions)
# Set AFP_VersionCompare=No to list all versions regardless of content
export AFP_FromYear=""
# Set AFP_FromYear to a year (e.g., 2020) to ignore resources before that year. Leave empty to include all years.
export AFP_AllNameSpaces="No"
# Set AFP_AllNameSpaces=Yes to combine resources from all namespaces into a single list (requires AFP_VersionCompare=Yes)
# Set AFP_AllNameSpaces=No to keep namespaces separate (default)

# AFP Resources Export
export AFP_Export_SG="${Migration_data}/AFP_Export_SG"
export AFP_Export_MY="${Migration_data}/AFP_Export_MY"
