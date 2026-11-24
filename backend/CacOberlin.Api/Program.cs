using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Reflection;
using System.Text.Json;
using Microsoft.Data.Sqlite;

SQLitePCL.raw.SetProvider(OperatingSystem.IsWindows()
    ? new SQLitePCL.SQLite3Provider_winsqlite3()
    : new SQLitePCL.SQLite3Provider_sqlite3());

var builder = WebApplication.CreateBuilder(args);
var configuredDatabasePath = Environment.GetEnvironmentVariable("PRIMERA_ESCUCHA_DB");
var databasePath = string.IsNullOrWhiteSpace(configuredDatabasePath)
    ? Path.GetFullPath(Path.Combine(builder.Environment.ContentRootPath, "..", "data", "CACOberlin.db"))
    : Path.GetFullPath(configuredDatabasePath);

builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
});
builder.Services.AddCors();
builder.Services.AddSingleton(new Database(databasePath));

var app = builder.Build();

app.UseCors(policy => policy
    .WithOrigins("http://localhost:4200", "http://127.0.0.1:4200")
    .WithMethods("GET", "POST", "PUT", "DELETE")
    .WithHeaders("Content-Type"));

app.Services.GetRequiredService<Database>().Initialize();

app.MapGet("/api/health", () => Results.Ok(new { status = "ok" }));

app.MapGet("/api/records", (string? search, string? consult_type, Database database) =>
{
    if (search?.Length > 160)
        return ValidationError(nameof(search), "Ensure this value has at most 160 characters.");
    if (consult_type is not null and not ("directa" or "indirecta"))
        return ValidationError(nameof(consult_type), "Input should be 'directa' or 'indirecta'.");
    return Results.Ok(database.ListRecords(search, consult_type));
});

app.MapPost("/api/records", (RecordInput input, Database database) =>
{
    var errors = Validate(input);
    if (input.ConsultType is not ("directa" or "indirecta"))
        errors["consult_type"] = ["Input should be 'directa' or 'indirecta'."];
    if (!DateOnly.TryParseExact(input.RecordDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out _))
        errors["record_date"] = ["Input should be a valid date in YYYY-MM-DD format."];
    return errors.Count > 0
        ? Results.ValidationProblem(errors, statusCode: StatusCodes.Status422UnprocessableEntity)
        : Results.Json(database.CreateRecord(input), statusCode: StatusCodes.Status201Created);
});

app.MapGet("/api/records/{recordId:int}", (int recordId, Database database) =>
    database.GetRecord(recordId) is { } record
        ? Results.Ok(record)
        : NotFound("No se encontró el registro."));

app.MapPut("/api/records/{recordId:int}", (int recordId, RecordInput input, Database database) =>
{
    var errors = Validate(input);
    if (input.ConsultType is not ("directa" or "indirecta"))
        errors["consult_type"] = ["Input should be 'directa' or 'indirecta'."];
    if (!DateOnly.TryParseExact(input.RecordDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out _))
        errors["record_date"] = ["Input should be a valid date in YYYY-MM-DD format."];
    if (errors.Count > 0)
        return Results.ValidationProblem(errors, statusCode: StatusCodes.Status422UnprocessableEntity);
    var record = database.UpdateRecord(recordId, input);
    return record is null ? NotFound("No se encontró el registro.") : Results.Ok(record);
});

app.MapDelete("/api/records/{recordId:int}", (int recordId, Database database) =>
    database.DeleteRecord(recordId)
        ? Results.NoContent()
        : NotFound("No se encontró el registro."));

app.MapGet("/api/contacts", (Database database) => Results.Ok(database.ListContacts()));

app.MapPost("/api/contacts", (ContactInput input, Database database) =>
{
    var errors = Validate(input);
    return errors.Count > 0
        ? Results.ValidationProblem(errors, statusCode: StatusCodes.Status422UnprocessableEntity)
        : Results.Json(database.CreateContact(input), statusCode: StatusCodes.Status201Created);
});

app.MapGet("/api/contacts/{contactId:int}", (int contactId, Database database) =>
    database.GetContact(contactId) is { } contact
        ? Results.Ok(contact)
        : NotFound("No se encontró el primer contacto."));

app.MapPut("/api/contacts/{contactId:int}", (int contactId, ContactInput input, Database database) =>
{
    var errors = Validate(input);
    if (errors.Count > 0)
        return Results.ValidationProblem(errors, statusCode: StatusCodes.Status422UnprocessableEntity);
    var contact = database.UpdateContact(contactId, input);
    return contact is null ? NotFound("No se encontró el primer contacto.") : Results.Ok(contact);
});

app.MapDelete("/api/contacts/{contactId:int}", (int contactId, Database database) =>
    database.DeleteContact(contactId)
        ? Results.NoContent()
        : NotFound("No se encontró el primer contacto."));

app.MapGet("/api/residences", (Database database) => Results.Ok(database.ListResidences()));

app.MapPost("/api/residences", (ResidenceInput input, Database database) =>
{
    var errors = Validate(input);
    return errors.Count > 0
        ? Results.ValidationProblem(errors, statusCode: StatusCodes.Status422UnprocessableEntity)
        : Results.Json(database.CreateResidence(input), statusCode: StatusCodes.Status201Created);
});

app.MapPut("/api/residences/{residenceId:int}", (int residenceId, ResidenceInput input, Database database) =>
{
    var errors = Validate(input);
    if (errors.Count > 0)
        return Results.ValidationProblem(errors, statusCode: StatusCodes.Status422UnprocessableEntity);
    var residence = database.UpdateResidence(residenceId, input);
    return residence is null ? NotFound("No se encontró la residencia.") : Results.Ok(residence);
});

app.Run("http://127.0.0.1:8000");

static IResult NotFound(string detail) => Results.NotFound(new { detail });

static IResult ValidationError(string name, string detail) =>
    Results.ValidationProblem(new Dictionary<string, string[]> { [JsonNamingPolicy.SnakeCaseLower.ConvertName(name)] = [detail] },
        statusCode: StatusCodes.Status422UnprocessableEntity);

static Dictionary<string, string[]> Validate(object value)
{
    foreach (var property in value.GetType().GetProperties(BindingFlags.Instance | BindingFlags.Public))
    {
        if (property.PropertyType == typeof(string) && property.GetValue(value) is string text)
            property.SetValue(value, text.Trim());
    }

    var results = new List<ValidationResult>();
    Validator.TryValidateObject(value, new ValidationContext(value), results, validateAllProperties: true);
    return results
        .SelectMany(result => (result.MemberNames.Any() ? result.MemberNames : [""]).Select(member =>
            (Member: JsonNamingPolicy.SnakeCaseLower.ConvertName(member), Error: result.ErrorMessage ?? "Invalid value.")))
        .GroupBy(item => item.Member)
        .ToDictionary(group => group.Key, group => group.Select(item => item.Error).ToArray());
}

public sealed class RecordInput
{
    [Required]
    public string RecordDate { get; set; } = "";
    [Required]
    public string ConsultType { get; set; } = "";
    [Required, StringLength(160, MinimumLength = 2)]
    public string FullName { get; set; } = "";
    [StringLength(240)]
    public string? Address { get; set; }
    [StringLength(32)]
    public string? Dni { get; set; }
    [StringLength(80)]
    public string? Kinship { get; set; }
    [Required, StringLength(5000, MinimumLength = 3)]
    public string Consultation { get; set; } = "";
    [StringLength(2000)]
    public string? Referral { get; set; }
}

public sealed class ListeningRecord
{
    public int Id { get; init; }
    public string RecordDate { get; init; } = "";
    public string ConsultType { get; init; } = "";
    public string FullName { get; init; } = "";
    public string? Address { get; init; }
    public string? Dni { get; init; }
    public string? Kinship { get; init; }
    public string Consultation { get; init; } = "";
    public string? Referral { get; init; }
    public string CreatedAt { get; init; } = "";
}

public class ContactInput
{
    [StringLength(240)] public string? DateAndPlace { get; set; }
    [Required, StringLength(160, MinimumLength = 2)] public string FullName { get; set; } = "";
    [StringLength(40)] public string? BirthDate { get; set; }
    [StringLength(240)] public string? SelfPerceivedGender { get; set; }
    [StringLength(32)] public string? Dni { get; set; }
    [StringLength(2000)] public string? HousingSituation { get; set; }
    [StringLength(500)] public string? ResidenceAddress { get; set; }
    [StringLength(80)] public string? Phone { get; set; }
    [StringLength(80)] public string? ContactDatetime { get; set; }
    [StringLength(2000)] public string? AccessMode { get; set; }
    [StringLength(5000)] public string? ManifestDemand { get; set; }
    [StringLength(5000)] public string? LatentDemand { get; set; }
    [StringLength(5000)] public string? AffectiveReferences { get; set; }
    [StringLength(5000)] public string? HouseholdStructure { get; set; }
    [StringLength(2000)] public string? Literacy { get; set; }
    [StringLength(2000)] public string? EducationLevel { get; set; }
    [StringLength(2000)] public string? EmploymentSituation { get; set; }
    [StringLength(80)] public string? Disability { get; set; }
    [StringLength(2000)] public string? DisabilityDetails { get; set; }
    [StringLength(5000)] public string? Health { get; set; }
    [StringLength(80)] public string? ViolencePresent { get; set; }
    [StringLength(3000)] public string? ViolenceDetails { get; set; }
    [StringLength(2000)] public string? LegalConflict { get; set; }
    [StringLength(3000)] public string? RightsAccessibility { get; set; }
    [StringLength(2000)] public string? Substance { get; set; }
    [StringLength(1000)] public string? Frequency { get; set; }
    [StringLength(3000)] public string? MedicationTreatment { get; set; }
    [StringLength(3000)] public string? ConsumptionObservations { get; set; }
    [StringLength(5000)] public string? PreviousTreatments { get; set; }
    [StringLength(5000)] public string? FirstResponse { get; set; }
    [StringLength(3000)] public string? AccompanimentProposals { get; set; }
    [StringLength(3000)] public string? ParticipationActivities { get; set; }
    [StringLength(1000)] public string? Activity { get; set; }
    [StringLength(500)] public string? ActivityDayTime { get; set; }
    [StringLength(500)] public string? ActivityPlace { get; set; }
    [StringLength(500)] public string? ActivityReferent { get; set; }
    [StringLength(5000)] public string? SecondResponse { get; set; }
    [StringLength(5000)] public string? FollowUpObservations { get; set; }
}

public sealed class ContactRecord : ContactInput
{
    public int Id { get; init; }
    public string CreatedAt { get; init; } = "";
}

public class ResidenceInput
{
    [Required, StringLength(160, MinimumLength = 2)]
    public string NombreQuerido { get; set; } = "";
    [Required(AllowEmptyStrings = true), StringLength(500)]
    public string Direccion { get; set; } = "";
    [Range(0, 100000)]
    public int Ocupacion { get; set; }
    [Range(0, 100000)]
    public int Capacidad { get; set; }
}

public sealed class ResidenceRecord : ResidenceInput
{
    public int Id { get; init; }
    public string CreatedAt { get; init; } = "";
}

public sealed class Database(string path)
{
    private static readonly JsonSerializerOptions DataJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private string ConnectionString => new SqliteConnectionStringBuilder { DataSource = path }.ToString();

    private SqliteConnection Open()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var connection = new SqliteConnection(ConnectionString);
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "PRAGMA foreign_keys = ON";
        command.ExecuteNonQuery();
        return connection;
    }

    public void Initialize()
    {
        using var connection = Open();
        using var transaction = connection.BeginTransaction();
        var tables = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using (var command = connection.CreateCommand())
        {
            command.Transaction = transaction;
            command.CommandText = "SELECT name FROM sqlite_master WHERE type = 'table'";
            using var reader = command.ExecuteReader();
            while (reader.Read())
                tables.Add(reader.GetString(0));
        }

        if (tables.Contains("records") && tables.Contains("PrimeraConsulta"))
            throw new InvalidOperationException("No se puede renombrar records: records y PrimeraConsulta existen.");
        if (tables.Contains("records"))
            Execute(connection, transaction, "ALTER TABLE records RENAME TO \"PrimeraConsulta\"");
        Execute(connection, transaction, """
            CREATE TABLE IF NOT EXISTS "PrimeraConsulta" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT NOT NULL,
                consult_type TEXT NOT NULL CHECK (consult_type IN ('directa', 'indirecta')),
                full_name TEXT NOT NULL,
                address TEXT,
                dni TEXT,
                kinship TEXT,
                consultation TEXT NOT NULL,
                referral TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """);

        if (tables.Contains("contacts") && tables.Contains("primerContacto"))
            throw new InvalidOperationException("No se puede renombrar contacts: contacts y primerContacto existen.");
        if (tables.Contains("contacts"))
            Execute(connection, transaction, "ALTER TABLE contacts RENAME TO \"primerContacto\"");
        Execute(connection, transaction, """
            CREATE TABLE IF NOT EXISTS "primerContacto" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """);
        Execute(connection, transaction, """
            CREATE TABLE IF NOT EXISTS "Residencias" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_querido TEXT NOT NULL,
                direccion TEXT NOT NULL DEFAULT '',
                ocupacion INTEGER NOT NULL DEFAULT 0 CHECK (ocupacion >= 0),
                capacidad INTEGER NOT NULL DEFAULT 0 CHECK (capacidad >= 0),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """);

        string? ocupacionType = null;
        using (var command = connection.CreateCommand())
        {
            command.Transaction = transaction;
            command.CommandText = "PRAGMA table_info(\"Residencias\")";
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                if (reader.GetString(1) == "ocupacion")
                    ocupacionType = reader.GetString(2);
            }
        }

        if (ocupacionType is not null && !string.Equals(ocupacionType, "INTEGER", StringComparison.OrdinalIgnoreCase))
        {
            Execute(connection, transaction, "ALTER TABLE \"Residencias\" RENAME TO \"Residencias_old\"");
            Execute(connection, transaction, """
                CREATE TABLE "Residencias" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_querido TEXT NOT NULL,
                    direccion TEXT NOT NULL DEFAULT '',
                    ocupacion INTEGER NOT NULL DEFAULT 0 CHECK (ocupacion >= 0),
                    capacidad INTEGER NOT NULL DEFAULT 0 CHECK (capacidad >= 0),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """);
            Execute(connection, transaction, """
                INSERT INTO "Residencias"
                    (id, nombre_querido, direccion, ocupacion, capacidad, created_at, updated_at)
                SELECT id, nombre_querido, COALESCE(direccion, ''),
                    CASE WHEN typeof(ocupacion) = 'integer' THEN ocupacion ELSE 0 END,
                    CASE WHEN typeof(capacidad) = 'integer' AND capacidad >= 0 THEN capacidad ELSE 0 END,
                    created_at, updated_at
                FROM "Residencias_old"
                """);
            Execute(connection, transaction, "DROP TABLE \"Residencias_old\"");
        }

        transaction.Commit();
    }

    public List<ListeningRecord> ListRecords(string? search, string? consultType)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        var conditions = new List<string>();
        if (!string.IsNullOrEmpty(search))
        {
            conditions.Add("(full_name LIKE $search OR dni LIKE $search OR consultation LIKE $search OR referral LIKE $search)");
            command.Parameters.AddWithValue("$search", $"%{search.Trim()}%");
        }
        if (consultType is not null)
        {
            conditions.Add("consult_type = $consultType");
            command.Parameters.AddWithValue("$consultType", consultType);
        }
        command.CommandText = $"SELECT * FROM \"PrimeraConsulta\" {(conditions.Count == 0 ? "" : "WHERE " + string.Join(" AND ", conditions))} ORDER BY record_date DESC, id DESC";
        using var reader = command.ExecuteReader();
        var records = new List<ListeningRecord>();
        while (reader.Read())
            records.Add(ReadRecord(reader));
        return records;
    }

    public ListeningRecord? GetRecord(int id)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM \"PrimeraConsulta\" WHERE id = $id";
        command.Parameters.AddWithValue("$id", id);
        using var reader = command.ExecuteReader();
        return reader.Read() ? ReadRecord(reader) : null;
    }

    public ListeningRecord CreateRecord(RecordInput input)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO "PrimeraConsulta"
                (record_date, consult_type, full_name, address, dni, kinship, consultation, referral)
            VALUES ($date, $type, $name, $address, $dni, $kinship, $consultation, $referral);
            SELECT last_insert_rowid();
            """;
        AddRecordParameters(command, input);
        return GetRecord(Convert.ToInt32(command.ExecuteScalar(), CultureInfo.InvariantCulture))!;
    }

    public ListeningRecord? UpdateRecord(int id, RecordInput input)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            UPDATE "PrimeraConsulta" SET record_date=$date, consult_type=$type, full_name=$name,
                address=$address, dni=$dni, kinship=$kinship, consultation=$consultation, referral=$referral
            WHERE id=$id
            """;
        AddRecordParameters(command, input);
        command.Parameters.AddWithValue("$id", id);
        return command.ExecuteNonQuery() == 0 ? null : GetRecord(id);
    }

    public bool DeleteRecord(int id) => DeleteById("\"PrimeraConsulta\"", id);

    public List<ContactRecord> ListContacts()
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, data_json, created_at FROM \"primerContacto\" ORDER BY id DESC";
        using var reader = command.ExecuteReader();
        var contacts = new List<ContactRecord>();
        while (reader.Read())
            contacts.Add(ReadContact(reader));
        return contacts;
    }

    public ContactRecord? GetContact(int id)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, data_json, created_at FROM \"primerContacto\" WHERE id=$id";
        command.Parameters.AddWithValue("$id", id);
        using var reader = command.ExecuteReader();
        return reader.Read() ? ReadContact(reader) : null;
    }

    public ContactRecord CreateContact(ContactInput input)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = "INSERT INTO \"primerContacto\" (full_name, data_json) VALUES ($name, $json); SELECT last_insert_rowid();";
        command.Parameters.AddWithValue("$name", input.FullName);
        command.Parameters.AddWithValue("$json", JsonSerializer.Serialize(input, DataJsonOptions));
        return GetContact(Convert.ToInt32(command.ExecuteScalar(), CultureInfo.InvariantCulture))!;
    }

    public ContactRecord? UpdateContact(int id, ContactInput input)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            UPDATE "primerContacto" SET full_name=$name, data_json=$json, updated_at=datetime('now')
            WHERE id=$id
            """;
        command.Parameters.AddWithValue("$name", input.FullName);
        command.Parameters.AddWithValue("$json", JsonSerializer.Serialize(input, DataJsonOptions));
        command.Parameters.AddWithValue("$id", id);
        return command.ExecuteNonQuery() == 0 ? null : GetContact(id);
    }

    public bool DeleteContact(int id) => DeleteById("\"primerContacto\"", id);

    public List<ResidenceRecord> ListResidences()
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, nombre_querido, direccion, ocupacion, capacidad, created_at FROM \"Residencias\" ORDER BY nombre_querido COLLATE NOCASE, id";
        using var reader = command.ExecuteReader();
        var residences = new List<ResidenceRecord>();
        while (reader.Read())
            residences.Add(ReadResidence(reader));
        return residences;
    }

    public ResidenceRecord? GetResidence(int id)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, nombre_querido, direccion, ocupacion, capacidad, created_at FROM \"Residencias\" WHERE id=$id";
        command.Parameters.AddWithValue("$id", id);
        using var reader = command.ExecuteReader();
        return reader.Read() ? ReadResidence(reader) : null;
    }

    public ResidenceRecord CreateResidence(ResidenceInput input)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO "Residencias" (nombre_querido, direccion, ocupacion, capacidad)
            VALUES ($name, $address, $occupied, $capacity);
            SELECT last_insert_rowid();
            """;
        AddResidenceParameters(command, input);
        return GetResidence(Convert.ToInt32(command.ExecuteScalar(), CultureInfo.InvariantCulture))!;
    }

    public ResidenceRecord? UpdateResidence(int id, ResidenceInput input)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            UPDATE "Residencias" SET nombre_querido=$name, direccion=$address, ocupacion=$occupied,
                capacidad=$capacity, updated_at=datetime('now') WHERE id=$id
            """;
        AddResidenceParameters(command, input);
        command.Parameters.AddWithValue("$id", id);
        return command.ExecuteNonQuery() == 0 ? null : GetResidence(id);
    }

    private bool DeleteById(string table, int id)
    {
        using var connection = Open();
        using var command = connection.CreateCommand();
        command.CommandText = $"DELETE FROM {table} WHERE id=$id";
        command.Parameters.AddWithValue("$id", id);
        return command.ExecuteNonQuery() > 0;
    }

    private static void Execute(SqliteConnection connection, SqliteTransaction transaction, string sql)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    private static void AddRecordParameters(SqliteCommand command, RecordInput input)
    {
        command.Parameters.AddWithValue("$date", input.RecordDate);
        command.Parameters.AddWithValue("$type", input.ConsultType);
        command.Parameters.AddWithValue("$name", input.FullName);
        command.Parameters.AddWithValue("$address", (object?)input.Address ?? DBNull.Value);
        command.Parameters.AddWithValue("$dni", (object?)input.Dni ?? DBNull.Value);
        command.Parameters.AddWithValue("$kinship", (object?)input.Kinship ?? DBNull.Value);
        command.Parameters.AddWithValue("$consultation", input.Consultation);
        command.Parameters.AddWithValue("$referral", (object?)input.Referral ?? DBNull.Value);
    }

    private static void AddResidenceParameters(SqliteCommand command, ResidenceInput input)
    {
        command.Parameters.AddWithValue("$name", input.NombreQuerido);
        command.Parameters.AddWithValue("$address", input.Direccion);
        command.Parameters.AddWithValue("$occupied", input.Ocupacion);
        command.Parameters.AddWithValue("$capacity", input.Capacidad);
    }

    private static ListeningRecord ReadRecord(SqliteDataReader reader) => new()
    {
        Id = reader.GetInt32(0),
        RecordDate = reader.GetString(1),
        ConsultType = reader.GetString(2),
        FullName = reader.GetString(3),
        Address = NullableString(reader, 4),
        Dni = NullableString(reader, 5),
        Kinship = NullableString(reader, 6),
        Consultation = reader.GetString(7),
        Referral = NullableString(reader, 8),
        CreatedAt = reader.GetString(9)
    };

    private static ContactRecord ReadContact(SqliteDataReader reader)
    {
        var input = JsonSerializer.Deserialize<ContactInput>(reader.GetString(1), DataJsonOptions) ?? new ContactInput();
        return new ContactRecord
        {
            DateAndPlace = input.DateAndPlace,
            FullName = input.FullName,
            BirthDate = input.BirthDate,
            SelfPerceivedGender = input.SelfPerceivedGender,
            Dni = input.Dni,
            HousingSituation = input.HousingSituation,
            ResidenceAddress = input.ResidenceAddress,
            Phone = input.Phone,
            ContactDatetime = input.ContactDatetime,
            AccessMode = input.AccessMode,
            ManifestDemand = input.ManifestDemand,
            LatentDemand = input.LatentDemand,
            AffectiveReferences = input.AffectiveReferences,
            HouseholdStructure = input.HouseholdStructure,
            Literacy = input.Literacy,
            EducationLevel = input.EducationLevel,
            EmploymentSituation = input.EmploymentSituation,
            Disability = input.Disability,
            DisabilityDetails = input.DisabilityDetails,
            Health = input.Health,
            ViolencePresent = input.ViolencePresent,
            ViolenceDetails = input.ViolenceDetails,
            LegalConflict = input.LegalConflict,
            RightsAccessibility = input.RightsAccessibility,
            Substance = input.Substance,
            Frequency = input.Frequency,
            MedicationTreatment = input.MedicationTreatment,
            ConsumptionObservations = input.ConsumptionObservations,
            PreviousTreatments = input.PreviousTreatments,
            FirstResponse = input.FirstResponse,
            AccompanimentProposals = input.AccompanimentProposals,
            ParticipationActivities = input.ParticipationActivities,
            Activity = input.Activity,
            ActivityDayTime = input.ActivityDayTime,
            ActivityPlace = input.ActivityPlace,
            ActivityReferent = input.ActivityReferent,
            SecondResponse = input.SecondResponse,
            FollowUpObservations = input.FollowUpObservations,
            Id = reader.GetInt32(0),
            CreatedAt = reader.GetString(2)
        };
    }

    private static ResidenceRecord ReadResidence(SqliteDataReader reader) => new()
    {
        Id = reader.GetInt32(0),
        NombreQuerido = reader.GetString(1),
        Direccion = reader.GetString(2),
        Ocupacion = reader.GetInt32(3),
        Capacidad = reader.GetInt32(4),
        CreatedAt = reader.GetString(5)
    };

    private static string? NullableString(SqliteDataReader reader, int ordinal) =>
        reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);
}
