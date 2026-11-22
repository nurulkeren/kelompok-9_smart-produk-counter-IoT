<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'index'])->name('dashboard');
Route::get('/live-data', [DashboardController::class, 'liveData'])->name('live.data');
Route::post('/reset-logs', [DashboardController::class, 'resetLogs'])->name('logs.reset');
Route::post('/batches', [DashboardController::class, 'storeBatch'])->name('batches.store');
Route::post('/products', [DashboardController::class, 'storeProduct'])->name('products.store');
Route::get('/export-csv', [DashboardController::class, 'exportCsv'])->name('export.csv');