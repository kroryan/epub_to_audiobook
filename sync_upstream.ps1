# Script para sincronizar con el repositorio upstream
# Uso: .\sync_upstream.ps1

Write-Host "Sincronizando con el repositorio upstream..." -ForegroundColor Green

# Cambiar a la rama main
git checkout main

# Obtener los últimos cambios del upstream
Write-Host "Obteniendo cambios del upstream..." -ForegroundColor Yellow
git fetch upstream

# Verificar si hay nuevos cambios
$upstreamCommit = git rev-parse upstream/main
$currentCommit = git rev-parse HEAD

if ($upstreamCommit -eq $currentCommit) {
    Write-Host "Tu repositorio ya está actualizado con upstream/main" -ForegroundColor Green
} else {
    Write-Host "Hay nuevos cambios en upstream. Mostrando diferencias..." -ForegroundColor Yellow
    git log --oneline HEAD..upstream/main
    
    $response = Read-Host "¿Quieres mergear estos cambios? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        # Crear una rama backup antes del merge
        $backupBranch = "backup-antes-merge-$(Get-Date -Format 'yyyy-MM-dd-HHmm')"
        git checkout -b $backupBranch
        git checkout main
        
        Write-Host "Mergeando cambios de upstream..." -ForegroundColor Yellow
        git merge upstream/main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Merge completado exitosamente" -ForegroundColor Green
            Write-Host "Subiendo cambios a tu fork..." -ForegroundColor Yellow
            git push origin main
            Write-Host "Sincronización completa!" -ForegroundColor Green
        } else {
            Write-Host "Error en el merge. Resuelve los conflictos manualmente." -ForegroundColor Red
        }
    }
}