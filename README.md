# MES Ignition 4.0 - PostgreSQL Compatible

This repository contains the MES Ignition 4.0 project with PostgreSQL database compatibility.

## Repository Structure

### Main Project
The main Ignition Perspective project is located in:
- `com.inductiveautomation.perspective/` - All Perspective views and configurations

### Script Library
The mes_core Python script library is located in:
- `mes_core_scripts/mes_core/` - Python script modules for MES functionality

## Installation

### Option 1: Full Installation (Recommended)
Clone the entire repository to get both the project and script library:
```bash
git clone https://github.com/rlesovsky/mes_Ignition_4.0.git
cd mes_Ignition_4.0
git checkout postgres-queries
```

### Option 2: Import Scripts Only
If you only need the script library:
1. Clone the repository
2. Copy the `mes_core_scripts/mes_core/` folder to your Ignition gateway's script library
3. The scripts are located at: `ignition/script-python/mes_core/`

### Option 3: Import Project Only
If you only need the Perspective views:
1. Clone the repository
2. Import the project from `com.inductiveautomation.perspective/`

## Script Library Modules

The `mes_core_scripts/mes_core/` folder contains:
- **count** - Count history logging
- **logging** - MES logging utilities
- **model** - MES object model queries (Enterprise, Site, Area, Line, Cell)
- **oee** - OEE calculation functions
- **order** - Work order management
- **run** - Run management (start, stop, update)
- **state** - State history management

## Database Compatibility

All SQL queries have been updated for PostgreSQL compatibility:
- Column names use lowercase
- Boolean values use `true`/`false` instead of `1`/`0`
- Date/time functions use PostgreSQL syntax
- String concatenation uses `||` operator

## Branch Information

- **postgres-queries** - Main branch with PostgreSQL-compatible code

## Usage

### Importing Scripts into Ignition
1. Copy the `mes_core_scripts/mes_core/` folder to your Ignition gateway
2. Place it in: `[Ignition Installation]/data/script-python/mes_core/`
3. Restart the Ignition gateway
4. Scripts will be available as `mes_core.count`, `mes_core.oee`, etc.

### Importing Project
1. In Ignition Designer, go to File > Import Project
2. Select the `com.inductiveautomation.perspective/` folder
3. The project will be imported with all views and configurations

## Notes

- All scripts have been refactored for PostgreSQL compatibility
- The project uses PostgreSQL database schema with lowercase column names
- Case-sensitive columns (like "TimeStamp") are properly quoted in queries

