param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Source,

    [Parameter(Position = 1)]
    [string]$DetailName = "detail",

    [Parameter(Position = 2)]
    [string]$SearchName = "search"
)

uv run python -m scripts.prepare_emby_fixture $Source $DetailName $SearchName
exit $LASTEXITCODE
