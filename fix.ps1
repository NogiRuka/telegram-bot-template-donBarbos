param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Source,

    [Parameter(Position = 1)]
    [string]$DetailName = "detail",

    [Parameter(Position = 2)]
    [string]$SearchName = "search"
)

# Examples:
#   .\fix.ps1 str8boys2023
#   .\fix.ps1 日韩/temp
uv run python -m scripts.prepare_emby_fixture $Source $DetailName $SearchName
$fixtureExitCode = $LASTEXITCODE
if ($fixtureExitCode -ne 0) {
    exit $fixtureExitCode
}

uv run python -m scripts.prepare_emby_cookie $Source
exit $LASTEXITCODE
