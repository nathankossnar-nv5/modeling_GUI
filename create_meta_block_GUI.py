"""
This script creates and/or checks the formatting of DWR MetaQC layers.
Fill in lines 18-22 with your information. Then run it. That's it!

The script will pause to allow you to manually assign or check the regions on the control sheet.
After checking the regions, just run it again (with the same parameters).
"""
import ast
import sys

import psycopg2
import psycopg2.extras
import yaml
from geopandas import GeoDataFrame


def fill_in_parameters():
    db = 'BLR'
    block_id = 252
    vector_layer = f'block_{block_id}_vector'
    max_grids_per_regions = 300

    ft_col_add = True

    return {'db': db, 'id': block_id, 'vector': vector_layer, 'max_grids': max_grids_per_regions, "ft": ft_col_add}

def get_db_config(db:str):
    """Loads database configuration from YAML file.

    Parameters:
        db (str): Database identifier (either "cvo" or "blr")..

    Returns:
        dict: Database configuration dictionary.

    Raises:
        ValueError: If YAML file not found or cannot be parsed.
    """
    if db.lower() in ("cvo", "blr"):
        yaml_path = f"W:/!Scripts/db_configs/{db}_script_user.yml"
    else:
        raise ValueError("Invalid db selected.")

    try:
        with open(yaml_path, "r") as yaml_file:
            return yaml.safe_load(yaml_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: YAML file not found at {yaml_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error while parsing YAML file at {yaml_path}: {e}")


def postgres_query(conn, sql_query, query_type, return_many=False, return_dict=False):
    """Executes SQL queries on PostgreSQL database.

    Parameters:
        conn (psycopg2.connection): Database connection object.
        sql_query (str): SQL query to execute.
        query_type (str): Type of query ('SELECT', 'UPDATE', 'DELETE').
        return_many (bool, optional): If True, returns all results as a list of tuples.
                                    If False, returns first result only as a tuple. Default False.
        return_dict (bool, optional): If True, returns results as RealDictRow list of tuples.
                                    If False, returns as list or tuple based on return_many. Default False.

    Returns:
        list, tuple, RealDictRow, or None: Query results or None for non-SELECT queries.
    """
    if return_dict:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = conn.cursor()

    cur.execute(sql_query)

    if query_type == "SELECT":
        if return_many:
            result = cur.fetchall()
        else:
            result = cur.fetchone()

    conn.commit()
    cur.close()

    return result if query_type == "SELECT" else None


def check_regions_exist(conn, schema, table_name):
    """
    Checks if the given table has a regions column and adds it if not.

    Parameters:
        conn (psycopg2 connection): A psycopg2 connection object.
        schema (str): DB schema where the table is stored.
        table_name (str): Name of the db table to check

    Returns:
        bool: Whether or not the regions column was found and/or added
    """
    exists_query = f"""SELECT EXISTS (SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}'
                    AND table_name = '{table_name}'
                    AND column_name = 'region')"""
    column_found = postgres_query(conn, exists_query, 'SELECT')[0]

    if not column_found:
        sql_query = f'ALTER TABLE {schema}.{table_name} ADD COLUMN region INTEGER;'
        postgres_query(conn, sql_query, 'UPDATE', True, True)

    return column_found

class MetaControlHandler():
    def __init__(self, conn, db, id, max_grids, auto_assign_region=True, schema='cadwr'):
        """
        Initializes a MetaControlHandler object.

        Parameters & Attributes:
            conn (psycopg2 connection): A psycopg2 connection object.
            id (int): The block id.
            max_grids (int): The maximum number of grids to include in one region.
            auto (bool): If True, regions will be automatically assinged to the control sheet.
                         If False (default), a number of regions will be suggested but not assigned.
            schema (str): The database schema where the meta control table is stored.
            name (str): The name of the meta control table.

        """
        self.conn = conn
        self.db = db
        self.id = id
        self.max_grids = max_grids
        self.auto = auto_assign_region
        self.schema = schema
        self.name = ''

    def check_permissions(self, schema, table_name, sequence=''):
        """
        Checks the permissions of the given table on the given db.

        Parameters:
            schema (str): The database schema where the table is located.
            table_name (str): The name of the table
            sequence (str): The name of a PostgreSQL sequence to check permissions for.
        """
        if self.db == 'CVO' or self.db == 'BLR':
            self.all_user_permissions(f"{schema}.{table_name}", sequence)
        else:
            print('DID NOT CHANGE ADDITIONAL PERMISSIONS')

    def all_user_permissions(self, full_table_name, sequence_name=""):
        """Grants appropriate permissions to all user groups for a database table.

        Parameters:
            conn (psycopg2.connection): Database connection object.
            db (str): Database identifier ('cvo' or 'blr') for user group selection.
            full_table_name (str): Full table name including schema (e.g., 'schema.table').
            sequence_name (str, optional): Sequence name for auto-increment fields. Defaults to "".

        """
        tool_user = "bangalore_tool_user" if self.db.lower() == "blr" else "cvo_tool_user"

        sql_query = f"""
            GRANT ALL PRIVILEGES ON TABLE {full_table_name} TO admin_user_group WITH GRANT OPTION;
            ALTER TABLE {full_table_name} OWNER TO admin_user_group;
            GRANT SELECT ON TABLE {full_table_name} TO read_only_user_group;
            GRANT DELETE, INSERT, UPDATE ON TABLE {full_table_name} TO write_user_group;
            GRANT SELECT, INSERT, UPDATE ON TABLE {full_table_name} TO {tool_user};
            GRANT SELECT, REFERENCES ON TABLE {full_table_name} TO metrics_tool_user;
        """

        if sequence_name:
            sql_query = (
                sql_query
                + f"""
            GRANT ALL ON SEQUENCE {sequence_name} TO write_user_group;
            GRANT ALL ON SEQUENCE {sequence_name} TO {tool_user};
            """
            )

        postgres_query(self.conn, sql_query, "UPDATE")

    def check_and_change_column_name(self, table_name, old_name, change=False):
        """
        Checks that the table has the correctly column name.

        Parameters:
            table_name (str): The name of the table to check
            old_name (str): The old column name
            change (bool, str): If False, just checks the the column exists.
                                If str, changes the column name to this str.

        Returns:
            bool: If the column name isn't changed, returns whether or not it exists.
        """
        query_str = f'''
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = '{self.schema}'
        AND table_name = '{table_name}'
        AND column_name = '{old_name}'
        '''
        old_name_detected = postgres_query(self.conn, query_str, 'SELECT', True, False)

        if old_name_detected and type(change) is str:   # Is the change parameter still necessary?
            sql_query = f'ALTER TABLE {self.schema}.{table_name} RENAME COLUMN "{old_name}" TO "{change}";'
            postgres_query(self.conn, sql_query, 'UPDATE', True, True)
        else:
            return old_name_detected

    def check_table_exists(self, substring, suffix='', could_be_multiple=False):
        """
        Checks if a table starting with "block_id_{suffix}" and containing a substring 
        exists on the db.

        Parameters:
            substring (str): String to check for in the table name (i.e., 'control', 'vector').
            suffix (str): Potential string phrase for in table name (i.e., 'qc', 'meta').
            could_be_multiple (bool): Checks for the suffix 'qc' first, the checks no suffix.

        Returns:
            bool: Whether or not a table was found.
        """
        if could_be_multiple:
            qc_exists =  self.check_table_exists(substring, 'qc')
            if not qc_exists:
                return self.check_table_exists(substring)
            else:
                return qc_exists
        query = f"""SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = '{self.schema}' and table_name like '%block_{self.id}_{suffix}%'"""
        possible_tables = postgres_query(self.conn, query, 'SELECT', True)
        if len(possible_tables) == 0:
            return False

        for tuple in possible_tables:
            table_name = tuple[0]
            if f'_{self.id}_' not in table_name:
                continue
            if suffix != 'meta' and 'meta' in table_name:
                continue
            if substring in table_name:
                return table_name
    
        return False

    def regions_assigned(self):
        """
        Returns whether or not there are multiple regions assigned to a table.
        """
        assigned_query = f'''SELECT COUNT(DISTINCT region) FROM {self.schema}.{self.name}'''
        assigned = postgres_query(self.conn, assigned_query, 'SELECT')[0] != 0
        if not assigned:
            self.number_regions()
        return assigned
    
    def already_dissolved(self):
        num_tiles_query = f'''SELECT COUNT(DISTINCT tile_index) FROM {self.schema}.{self.name}'''
        num_tiles = postgres_query(self.conn, num_tiles_query, 'SELECT')[0]

        old_num_tiles_query = f'''SELECT COUNT(DISTINCT tile_index) FROM {self.schema}.{self.get_old_control_name()} WHERE phase <> 88'''
        old_num_tiles = postgres_query(self.conn, old_num_tiles_query, 'SELECT')[0]

        return num_tiles < old_num_tiles

    def check_control_exists(self):
        """
        Returns whether or not a MetaQC control sheet exists on the database.
        """
        control_name = self.check_table_exists('control', 'meta')

        if type(control_name) is str:
            self.name = control_name
            return True
        return False

    def get_old_control_name(self):
        """
        Returns the name of a previous control sheet.
        Exits the script if nothing was found.
        """
        old_control = self.check_table_exists('control', '', True)
        if not old_control:
            print('Old control sheet could not be found.')
            sys.exit(1)
        return old_control

    def create_meta_control(self, control_name):
        """
        Copies all non-88'd tiles from the previous control sheet then
        creates and formats a new MetaQC control sheet.

        Parameters:
            control_name (str): Table name for the new control sheet on the database.
        """
        old_control = self.get_old_control_name()

        # Make new table
        full_name = f'{self.schema}.{control_name}'
        sequence_name = f'{full_name}_id_seq'
        
        copy_old_ctrl = f"""CREATE TABLE {full_name}  AS
                        SELECT geom, tile_index, phase
                        FROM {self.schema}.{old_control}
                        WHERE phase<>88;"""
        postgres_query(self.conn, copy_old_ctrl, 'UPDATE')

        seq_exists_query = f"""SELECT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE relkind = 'S'
            AND relname = '{control_name}_id_seq'
        );"""
        if not postgres_query(self.conn, seq_exists_query, 'SELECT')[0]:
            sql_query = f'CREATE SEQUENCE {sequence_name}'
            postgres_query(self.conn, sql_query, 'UPDATE', True, True)

        self.name = control_name
        self.set_pkey_seq('tile_index', sequence_name)

    def set_pkey_seq(self, primary_key_field, sequence):
        """
        Sets the proper permissions, primary key, and default tile_index sequence.
        """
        full_name = f'{self.schema}.{self.name}'
        
        self.check_permissions(self.schema, self.name, sequence)

        max_number = postgres_query(self.conn, f"SELECT MAX({primary_key_field}) FROM {full_name};", 'SELECT')[0]
        sql_query = (
            f'ALTER TABLE {full_name} ADD PRIMARY KEY ({primary_key_field}); '
            f'SELECT setval(\'{sequence}\', {max_number}, true); '
            f'ALTER TABLE {full_name} ALTER {primary_key_field} SET DEFAULT nextval(\'{sequence}\'::regclass); '
        )
        postgres_query(self.conn, sql_query, 'UPDATE', True, True)

    def dissolve_by_region(self):
        """
        Dissolves the MetaQC control sheet by region and adds meta editing columns.
        """
        full_name = f'{self.schema}.{self.name}'
        
        dissolve_query = f"""CREATE TABLE {self.schema}.temp  AS
                (SELECT region,
                ST_UNION(geom) as geom,
                array_agg(tile_index::integer) AS containing_tiles,
                0 AS tile_index
                FROM {full_name}
                WHERE phase <> 88
                GROUP BY region);
            DROP TABLE {full_name};
            ALTER TABLE {self.schema}.temp RENAME TO {self.name};"""
        postgres_query(self.conn, dissolve_query, 'UPDATE')

        self.check_permissions(self.schema, self.name)

        # Add control sheet columns with correct types and defaults
        add_cols_query = f"""ALTER TABLE {full_name} ADD COLUMN checked_out text;
            ALTER TABLE {full_name} ADD COLUMN phase INT DEFAULT 0;
            ALTER TABLE {full_name} ADD COLUMN priority INT DEFAULT 9;
            """
        if self.db == 'BLR':
            timezone = "AT TIME ZONE 'Asia/Kolkata'"
        else:
            timezone = "AT TIME ZONE 'America/Los_Angeles'"

        for phase in ['initial', 'second', 'third']:
            add_cols_query = add_cols_query + f"""ALTER TABLE {full_name} ADD COLUMN {phase}_digitizer text;"""
            
            for time in ['start', 'finish']:
                add_cols_query = add_cols_query + f"""ALTER TABLE {full_name} ADD COLUMN {phase}_{time} timestamptz(6) DEFAULT (CURRENT_TIMESTAMP {timezone});
                    UPDATE {full_name} SET {phase}_{time} = NULL;"""
            
            add_cols_query = add_cols_query + f"""ALTER TABLE {full_name} ADD COLUMN {phase}_timer float DEFAULT 0;"""

        postgres_query(self.conn, add_cols_query, 'UPDATE')
        
        # Column formatting queries
        sql_queries = (f'UPDATE {full_name} SET phase=0;'
                    f'UPDATE {full_name} SET tile_index=phase WHERE phase IS NOT NULL;'
                    f'DELETE FROM {full_name} WHERE tile_index IS NULL;'
                    f'UPDATE {full_name} SET tile_index=region;'
                    f'DELETE FROM {full_name} WHERE tile_index IS NULL;')
        
        postgres_query(self.conn, sql_queries, 'UPDATE', True, True)
    
    def number_regions(self):
        """
        Suggests or applies the optimal number of regions for the control sheet.

        If self.auto is True, the region column is updated accordingly.
        If self.auto is False, the optimal number of regions and grids/region is printed.
        """
        unmasked_tiles = self.count_non_88ed_tiles()

        # Calculate the minimum number of regions needed to satisfy max polygons constraint
        min_regions = unmasked_tiles // self.max_grids
        if unmasked_tiles % self.max_grids != 0:
            min_regions += 1  # Round up if there are remaining polygons

        optimal_regions = max(1, min_regions)

        # Calculate the approximate number of polygons per region
        tiles_per_region = unmasked_tiles // optimal_regions
        remainder = unmasked_tiles % optimal_regions

        if self.auto:
            # Auto:
            full_name = f'{self.schema}.{self.name}'
            update_sql = f'UPDATE {full_name} SET region=0;'
            
            for region_num in range(1,optimal_regions+1):
                update_sql += f' UPDATE {full_name} SET region={region_num} WHERE tile_index IN (SELECT tile_index FROM {full_name} WHERE region =0 AND phase != 88'
                if region_num != optimal_regions:
                    update_sql += f' ORDER BY tile_index LIMIT {tiles_per_region});'
                else:
                    update_sql += ');'
            postgres_query(self.conn, update_sql, 'UPDATE', True, True)

            print('Regions automatically applied.')
        else:
            # Manual
            print(f'Regions need to be manually applied to {self.name}.')
            print(f"Suggested number of regions: {optimal_regions} \tGrids per region: {tiles_per_region} ({remainder} remaining)")
    
    def count_non_88ed_tiles(self):
        """
        Returns the number of tiles that are not phase=88.
        """
        query_str = f'''SELECT COUNT(tile_index) FROM {self.schema}.{self.name} WHERE phase != 88'''
        return postgres_query(self.conn, query_str, 'SELECT', False, False)[0]

    def create_editing_grid(self):
        """
        Creates a tiled grid for MetaQC editing by region.
        Located in dwr_meta_grids.block_{id}_meta_grid.

        Returns:
            str: The name of the created editing grid.
        """
        old_control = self.get_old_control_name()
        grid_schema = 'dwr_meta_grids'
        editing_grid = f'block_{self.id}_meta_grid'

        
        drop_query = f"DROP TABLE IF EXISTS {grid_schema}.{editing_grid};"
        postgres_query(self.conn, drop_query, 'UPDATE')

        create_grid = f"""CREATE TABLE {grid_schema}.{editing_grid} AS
                            SELECT 
                            geom as geom,
                            tile_index as tile_index,
                            0 as complete
                            FROM {self.schema}.{old_control} as old
                            WHERE old.phase<>88"""
        postgres_query(self.conn, create_grid, 'UPDATE')

        pkey_query = f"""ALTER TABLE {grid_schema}.{editing_grid} ADD PRIMARY KEY (tile_index)"""
        postgres_query(self.conn, pkey_query, 'UPDATE')

        self.check_permissions(grid_schema, editing_grid)
        add_region_to_tiles(self.conn, self, grid_schema, editing_grid)

        return editing_grid

def add_region_to_tiles(conn, ctrl, update_schema, update_name):
    """
    Assigns appropriate region to tiles within the containing_tiles array.
    """
    check_regions_exist(conn, update_schema, update_name)
    sql_query = f"SELECT region, containing_tiles FROM {ctrl.schema}.{ctrl.name}"

    result = postgres_query(ctrl.conn, sql_query, 'SELECT', True, False)
    for row in result:
        # Convert the string to a list using ast.literal_eval
        float_list = ast.literal_eval(str(row[1]))

        tiles_list = ','.join(str(int(f)) for f in float_list)
        sql_update = f"UPDATE {update_schema}.{update_name} SET region ={row[0]} WHERE tile_index IN ({tiles_list})"
        postgres_query(ctrl.conn, sql_update, 'UPDATE')

def backup_vector(ctrl, block_folder, old_vector):
    """
    *Currently not in production
    Backs up the previous vector layer to the block folder.

    Parameters:
        ctrl (MetaControlHandler): The control sheet handler object for this block.
        old_vector (str): Name of the previously edited vector layer (up through QC).    
    """
    save_location = f'{block_folder}/{ctrl.schema}.{old_vector}_{ctrl.db}.gpkg'

    row_count_query = f'SELECT COUNT(*) FROM {ctrl.schema}.{old_vector}'
    row_count = postgres_query(ctrl.conn, row_count_query, 'SELECT', True)[0][0]

    print(f'Backing up {row_count} rows from {old_vector}.')
    query = f'SELECT * FROM "{ctrl.schema}"."{old_vector}"'
    gdf = GeoDataFrame.from_postgis(query, ctrl.conn, geom_col='geom')

    gdf.to_file(save_location, driver = "GPKG")
    print(f'QC layer backed up as {save_location}.')
    return save_location

def create_dissolved_vector(ctrl, old_vector, ft):
    """
    Creates a dissolved metaqc vector layer from non-88'd vector data.
    """
    new_vector = f'block_{ctrl.id}_metaqc_vector'
    
    get_tile_arrays = f"SELECT containing_tiles FROM {ctrl.schema}.{ctrl.name}"
    tile_arrays = postgres_query(ctrl.conn, get_tile_arrays, 'SELECT', True, False)

    tiles_list = ''
    for array in tile_arrays:
        # Convert the string to a list using ast.literal_eval
        float_list = ast.literal_eval(str(array[0]))
        tiles_list = tiles_list + ','.join(str(int(f)) for f in float_list) + ','
    tiles_list = tiles_list[:len(tiles_list) - 1]
    
    if not ft:
        ft_copy = ', func_turf_bool'
    else:
        ft_copy = ''
    
    create_query = f"""CREATE TABLE IF NOT EXISTS {ctrl.schema}.{new_vector} AS
                    (SELECT tile_index, class{ft_copy}, ST_Union(geom) as geom
                    FROM {ctrl.schema}.{old_vector} 
                    WHERE tile_index IN ({tiles_list})
                    GROUP BY tile_index, class{ft_copy});"""
    postgres_query(ctrl.conn, create_query, 'UPDATE')


    format_vector_query = (
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN key_value BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY;'
        f'CREATE INDEX idx_{new_vector}_geom ON {ctrl.schema}.{new_vector} USING gist (geom);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN region INTEGER;'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN area DOUBLE PRECISION;'
        f'UPDATE {ctrl.schema}.{new_vector} SET area = ST_Area(geom);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN x double precision;'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN y double precision;'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN og_class varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN init_ouid varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN init_class varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN init_agent varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN second_ouid varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN second_class varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN second_agent varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN third_ouid varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN third_class varchar(255);'
        f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN third_agent varchar(255);'
    )
    postgres_query(ctrl.conn, format_vector_query, 'UPDATE')

    index_query = f'CREATE INDEX tile_index_{new_vector} ON {ctrl.schema}.{new_vector} (tile_index);'
    postgres_query(conn, index_query, 'UPDATE', True, True)

    ctrl.check_permissions(ctrl.schema, new_vector)

    if ft:
        ft_query = f'ALTER TABLE {ctrl.schema}.{new_vector} ADD COLUMN IF NOT EXISTS func_turf_bool BIGINT DEFAULT 0;'
        postgres_query(ctrl.conn, ft_query, 'UPDATE')
        print('FT column added.')

    print(f'New layer {new_vector} created.')
    return new_vector

def add_project_dict_row(conn, control_handler, vector_name, grid_name):
    """
    Adds a DWR MetaQC row to the project_dictionaries table.

    Parameters:
        control_handler (object): MetaControlHandler object for the block's control sheet
        vector_name (str): Name of the vector layer to edit on the database.
        grid_name (str): Name of the editing grid table.
    """
    exclusion_name = control_handler.check_table_exists('exclusion','', True)
    if not exclusion_name:
        print('Exclusion layer not found.')
        return
    
    try:
        # Make previous project dictionary status = 3 and remove it from editor_priorities
        prev_dict = postgres_query(conn, f"UPDATE public.project_dictionaries SET status = 3 \
                                   WHERE name LIKE 'block_{control_handler.id}%' RETURNING name",
                                   'SELECT')[0]
        
        if control_handler.db.lower() != 'cvo':
            cvo_config = get_db_config('CVO')

            with psycopg2.connect(**cvo_config) as cvo_conn:
                postgres_query(cvo_conn, f"DELETE FROM public.editor_priorities WHERE tool_project_name = '{prev_dict}'",
                            'UPDATE')
        else:
            postgres_query(conn, f"DELETE FROM public.editor_priorities WHERE tool_project_name = '{prev_dict}'",
                            'UPDATE')
        
        # Create, validate, and upload new project_dict
        sys.path.insert(0, "W:/2023_CA_DWR_CII/1_Scripts/09_PostProcessing_LC/DB_Upload/")
        from add_dwr_project_dict import create_dwr_project_row
        create_dwr_project_row([control_handler.db, control_handler.id, True, 1, vector_name, exclusion_name, control_handler.name, grid_name])
        
        print(f'If table {vector_name} should not be the MetaQC editing layer, manually change the data_table in the project dictionary.')
        print(f'Block {ctrl.id} is ready for MetaQC in Divvy 2.0.')
    except Exception as e:
        print(f'Error adding block_{control_handler.id}_meta row to project dictionaries: {e}')

if __name__ == '__main__':
    params = fill_in_parameters()

    db_config = get_db_config(params['db'])

    with psycopg2.connect(**db_config) as conn:
        ctrl = MetaControlHandler(conn, params['db'], params['id'], params['max_grids'])
        # ctrl.name = f'block_{ctrl.id}_metaqc_control'
        # Check if control sheet already exists and make one if not
        if not ctrl.check_control_exists():
            ctrl.create_meta_control(f'block_{ctrl.id}_metaqc_control')
        
        # Check/Update permissions
        ctrl.check_permissions(ctrl.schema, ctrl.name)

        # Check/Update columns and formatting
        if not check_regions_exist(conn, ctrl.schema, ctrl.name) and not ctrl.regions_assigned():
            print(f'Check regions on {ctrl.name} for appropriateness before continuing.')
            sys.exit(0)
        else:
            if not ctrl.already_dissolved():
                ctrl.dissolve_by_region()
                ctrl.set_pkey_seq('tile_index', f'{ctrl.schema}.{ctrl.name}_id_seq')
            ctrl.check_and_change_column_name('Tile_Index', 'tile_index')

        # Make a MetaQC vector layer without 88'd data
        vector_layer = create_dissolved_vector(ctrl, params['vector'], params['ft'])
        
        #if metaqc layer already exists comment out line 607 and uncomment 610
        #vector_layer = params['vector']

        # Create editing grid
        grid_name = ctrl.create_editing_grid()

        # Add row to project_dictionaries
        add_project_dict_row(conn, ctrl, vector_layer, grid_name)