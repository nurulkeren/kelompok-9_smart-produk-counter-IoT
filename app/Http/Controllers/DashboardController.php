<?php

namespace App\Http\Controllers;

use App\Models\Batch;
use App\Models\Product;
use App\Models\ScanLog;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    public function index(Request $request)
    {
        $query = ScanLog::with(['batch', 'product'])->latest('waktu_scan');

        if ($request->filled('search')) {
            $s = $request->search;
            $query->where(function ($q) use ($s) {
                $q->where('uid_barcode', 'like', "%{$s}%")
                  ->orWhereHas('product', fn($p) => $p->where('nama_produk', 'like', "%{$s}%"))
                  ->orWhereHas('batch', fn($b) => $b->where('batch_code', 'like', "%{$s}%"));
            });
        }

        if ($request->filled('status')) {
            $query->where('status_scan', $request->status);
        }

        if ($request->filled('batch_id')) {
            $query->where('batch_id', $request->batch_id);
        }

        $logs = $query->paginate(10)->withQueryString();

        $totalValid  = ScanLog::where('status_scan', 'VALID')->count();
        $totalFailed = ScanLog::where('status_scan', 'FAILED')->count();
        $totalSemua  = $totalValid + $totalFailed;
        $akurasi     = $totalSemua > 0 ? round(($totalValid / $totalSemua) * 100, 1) : 100;

        $chartRows = ScanLog::select(
                DB::raw("DATE_FORMAT(waktu_scan, '%H:00') as jam"),
                DB::raw("SUM(CASE WHEN status_scan = 'VALID' THEN 1 ELSE 0 END) as valid_count"),
                DB::raw("SUM(CASE WHEN status_scan = 'FAILED' THEN 1 ELSE 0 END) as failed_count")
            )
            ->whereDate('waktu_scan', today())
            ->groupBy('jam')
            ->orderBy('jam')
            ->get();

        $batches  = Batch::latest()->get();
        $products = Product::with('batch')->latest()->get();

        return view('dashboard', compact(
            'logs', 'totalValid', 'totalFailed', 'akurasi',
            'chartRows', 'batches', 'products'
        ));
    }

    public function storeBatch(Request $request)
    {
        $data = $request->validate([
            'batch_code'    => 'required|string|max:30|unique:batches,batch_code',
            'nama_batch'    => 'required|string|max:100',
            'target_jumlah' => 'required|integer|min:1',
        ]);
        Batch::create($data + ['status' => 'AKTIF']);
        return back()->with('success', 'Batch produksi baru berhasil ditambahkan.');
    }

    public function storeProduct(Request $request)
    {
        $data = $request->validate([
            'batch_id'     => 'required|exists:batches,id',
            'product_code' => 'required|string|max:30|unique:products,product_code',
            'nama_produk'  => 'required|string|max:100',
            'berat_gram'   => 'required|integer|min:0',
        ]);
        Product::create($data);
        return back()->with('success', 'Master produk berhasil ditambahkan.');
    }

    public function exportCsv(Request $request)
    {
        $query = ScanLog::with(['batch', 'product'])->latest('waktu_scan');

        if ($request->filled('search')) {
            $query->where('uid_barcode', 'like', "%{$request->search}%");
        }
        if ($request->filled('status')) {
            $query->where('status_scan', $request->status);
        }
        if ($request->filled('batch_id')) {
            $query->where('batch_id', $request->batch_id);
        }

        $rows = $query->get();
        $filename = 'laporan_traceability_conveyor_' . now()->format('Ymd_His') . '.csv';

        $headers = [
            'Content-Type' => 'text/csv',
            'Content-Disposition' => "attachment; filename=\"$filename\"",
        ];

        $callback = function () use ($rows) {
            $file = fopen('php://output', 'w');
            fputcsv($file, ['No', 'Waktu Scan', 'UID Barcode', 'Kode Batch', 'Nama Produk', 'Tipe Kode', 'RPM Aktual', 'Status']);
            foreach ($rows as $i => $r) {
                fputcsv($file, [
                    $i + 1,
                    $r->waktu_scan?->format('Y-m-d H:i:s'),
                    $r->uid_barcode,
                    $r->batch->batch_code ?? '-',
                    $r->product->nama_produk ?? 'Umum / Non-Master',
                    $r->tipe_kode,
                    $r->rpm_saat_scan,
                    $r->status_scan,
                ]);
            }
            fclose($file);
        };

        return response()->stream($callback, 200, $headers);
    }
}