<!DOCTYPE html>
<html lang="id" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Conveyor Traceability & Control — Kelompok 9</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Plus Jakarta Sans', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }
        }
      }
    }
  </script>
  <style>
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #090d16; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }
  </style>
</head>
<body class="bg-[#090d16] text-slate-100 min-h-screen antialiased selection:bg-sky-500 selection:text-white">

  <!-- TOP NAVBAR -->
  <nav class="sticky top-0 z-30 bg-[#0d1322]/90 backdrop-blur-md border-b border-slate-800/80">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 17h16M4 17a3 3 0 01-3-3v-2a3 3 0 013-3h16a3 3 0 013 3v2a3 3 0 01-3 3M7 13h.01M12 13h.01M17 13h.01M8 9V5h8v4"/>
          </svg>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base sm:text-lg font-bold tracking-tight text-white">Smart Conveyor Traceability</h1>
            <span class="hidden sm:inline-block px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-sky-500/15 text-sky-400 border border-sky-500/30">
              Kelompok 9 IoT
            </span>
          </div>
          <p class="text-xs text-slate-400 hidden sm:block">PID Speed Stabilization, Vision Scanner & Production Audit</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <div id="mqtt-badge" class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <span id="mqtt-dot" class="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
          <span id="mqtt-text">Menghubungkan Broker...</span>
        </div>
      </div>
    </div>
  </nav>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

    @if(session('success'))
      <div class="flex items-center justify-between p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm">
        <div class="flex items-center gap-2.5">
          <svg class="w-5 h-5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>{{ session('success') }}</span>
        </div>
        <button onclick="this.parentElement.remove()" class="text-emerald-400 hover:text-white text-xs font-semibold">Tutup</button>
      </div>
    @endif

    @if($errors->any())
      <div class="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1">
        @foreach($errors->all() as $err)
          <p>• {{ $err }}</p>
        @endforeach
      </div>
    @endif

    <!-- KPI CARDS -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Status Mesin -->
      <div class="bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 shadow-sm relative overflow-hidden">
        <div class="flex items-center justify-between">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">Status Konveyor</p>
          <span class="p-2 rounded-lg bg-slate-800/80 text-slate-300">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          </span>
        </div>
        <p id="status-mesin" class="text-2xl font-bold font-mono mt-3 text-rose-400">OFF</p>
        <p id="status-detail" class="text-xs text-slate-400 mt-1.5">Saklar: OFF • Web: OFF</p>
      </div>

      <!-- Kecepatan PID -->
      <div class="bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">Kecepatan Sabuk (PID)</p>
          <span class="p-2 rounded-lg bg-sky-500/10 text-sky-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </span>
        </div>
        <div class="flex items-baseline gap-1.5 mt-3">
          <p id="live-rpm" class="text-2xl font-bold font-mono text-sky-400">0.0</p>
          <span class="text-xs font-semibold text-slate-400">RPM</span>
        </div>
        <p id="pid-detail" class="text-xs text-slate-400 mt-1.5 font-mono">Target: 100 RPM • PWM: 0</p>
      </div>

      <!-- Barang Lolos -->
      <div class="bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">Barang Lolos (Valid)</p>
          <span class="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
          </span>
        </div>
        <div class="flex items-baseline justify-between mt-3">
          <p id="live-valid" class="text-2xl font-bold font-mono text-emerald-400">{{ $totalValid }}</p>
          <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">Akurasi {{ $akurasi }}%</span>
        </div>
        <p id="last-uid" class="text-xs text-slate-400 mt-1.5 font-mono truncate">Terakhir: -</p>
      </div>

      <!-- Gagal Scan -->
      <div class="bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">Alert Tanpa Barcode</p>
          <span class="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          </span>
        </div>
        <p id="live-failed" class="text-2xl font-bold font-mono mt-3 text-amber-400">{{ $totalFailed }}</p>
        <p class="text-xs text-slate-400 mt-1.5">Barang lolos tanpa kode valid</p>
      </div>
    </section>

    <!-- KONTROL KONVEYOR & GENERATOR BARCODE -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Panel Kontrol Mesin (7 kolom) -->
      <div class="lg:col-span-7 bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 flex flex-col justify-between gap-5">
        <div>
          <h2 class="text-sm font-bold text-white uppercase tracking-wider">Kendali Operasi & Tuning PID</h2>
          <p class="text-xs text-slate-400 mt-0.5">Kirim perintah langsung ke ESP8266 dan Raspberry Pi melalui MQTT</p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button onclick="kirimPerintah('ON')" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-emerald-500/20 transition cursor-pointer">
            <span class="w-2 h-2 rounded-full bg-slate-950"></span> Jalankan (ON)
          </button>
          <button onclick="kirimPerintah('OFF')" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs uppercase tracking-wider shadow-lg shadow-rose-500/20 transition cursor-pointer">
            <span class="w-2 h-2 rounded-full bg-white"></span> Hentikan (OFF)
          </button>
          <button onclick="resetCounter()" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition cursor-pointer">
            Reset Counter & Memori Duplikat
          </button>
        </div>

        <div class="pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
          <div class="text-xs text-slate-400">
            <span class="font-semibold text-slate-200">Setpoint Kecepatan Sabuk:</span>
            Menjaga RPM konstan saat beban berubah
          </div>
          <div class="flex items-center gap-2">
            <div class="relative">
              <input id="input-rpm" type="number" value="100" min="30" max="300"
                     class="w-28 pl-3 pr-10 py-2 rounded-xl bg-slate-900 border border-slate-700 font-mono text-sm text-white focus:outline-none focus:border-sky-500">
              <span class="absolute right-3 top-2.5 text-[11px] font-mono text-slate-400">RPM</span>
            </div>
            <button onclick="ubahRPM()" class="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition cursor-pointer">
              Terapkan
            </button>
          </div>
        </div>
      </div>

      <!-- Generator & Cetak Label QR / Barcode (5 kolom) -->
      <div class="lg:col-span-5 bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 flex flex-col justify-between gap-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-sm font-bold text-white uppercase tracking-wider">Generator Label Barcode</h2>
            <p class="text-xs text-slate-400 mt-0.5">Buat & cetak kode UID sesuai master database</p>
          </div>
          <span class="px-2 py-1 rounded-md bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 text-[10px] font-bold">SIAP CETAK</span>
        </div>

        <div class="grid grid-cols-3 gap-2">
          <select id="gen-batch" onchange="generateLabel()" class="px-2.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white">
            @foreach($batches as $b)
              <option value="{{ $b->batch_code }}">{{ $b->batch_code }}</option>
            @endforeach
          </select>
          <select id="gen-prod" onchange="generateLabel()" class="px-2.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white">
            @foreach($products as $p)
              <option value="{{ $p->product_code }}">{{ $p->product_code }}</option>
            @endforeach
          </select>
          <input id="gen-seq" type="text" value="0001" oninput="generateLabel()" placeholder="Seri (0001)"
                 class="px-2.5 py-2 rounded-xl bg-slate-900 border border-slate-700 font-mono text-xs text-white">
        </div>

        <div class="flex items-center gap-4 bg-white rounded-xl p-3 text-slate-900">
          <div id="qr-preview" class="shrink-0"></div>
          <div class="flex-1 min-w-0">
            <p class="text-[10px] uppercase font-bold text-slate-400">Preview UID Barcode</p>
            <p id="uid-preview-text" class="font-mono font-bold text-sm text-slate-900 truncate">BCH2611-PRD01-0001</p>
            <svg id="barcode-1d-preview" class="w-full h-10 mt-1"></svg>
          </div>
          <button onclick="cetakLabel()" class="shrink-0 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold cursor-pointer">
            Cetak
          </button>
        </div>
      </div>
    </section>

    <!-- GRAFIK LAJU PRODUKSI & MASTER DATA -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Chart.js (8 kolom) -->
      <div class="lg:col-span-8 bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5">
        <div class="flex flex-wrap justify-between items-center gap-2 mb-4">
          <div>
            <h2 class="text-sm font-bold text-white uppercase tracking-wider">Visualisasi Laju Produksi Harian</h2>
            <p class="text-xs text-slate-400">Distribusi barang valid vs gagal pemindaian per jam</p>
          </div>
          <span class="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300">{{ now()->format('d M Y') }}</span>
        </div>
        <div class="h-64">
          <canvas id="productionChart"></canvas>
        </div>
      </div>

      <!-- Master Data Batch & Produk (4 kolom) -->
      <div class="lg:col-span-4 bg-[#0f172a] border border-slate-800/90 rounded-2xl p-5 space-y-5">
        <div>
          <h2 class="text-sm font-bold text-white uppercase tracking-wider">Master Batch & Produk</h2>
          <p class="text-xs text-slate-400 mt-0.5">Relasi data untuk pengelompokan hasil scan</p>
        </div>

        <form action="{{ route('batches.store') }}" method="POST" class="space-y-2.5 pb-4 border-b border-slate-800/80">
          @csrf
          <label class="block text-xs font-semibold text-sky-400">+ Tambah Batch Produksi</label>
          <div class="grid grid-cols-2 gap-2">
            <input type="text" name="batch_code" placeholder="Kode (BCH2612)" required class="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs font-mono uppercase">
            <input type="number" name="target_jumlah" placeholder="Target (100)" required class="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs">
          </div>
          <div class="flex gap-2">
            <input type="text" name="nama_batch" placeholder="Keterangan Batch..." required class="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs">
            <button type="submit" class="px-3.5 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold cursor-pointer">Simpan</button>
          </div>
        </form>

        <form action="{{ route('products.store') }}" method="POST" class="space-y-2.5">
          @csrf
          <label class="block text-xs font-semibold text-emerald-400">+ Tambah Master Produk</label>
          <select name="batch_id" required class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs">
            @foreach($batches as $b)
              <option value="{{ $b->id }}">{{ $b->batch_code }} — {{ $b->nama_batch }}</option>
            @endforeach
          </select>
          <div class="grid grid-cols-2 gap-2">
            <input type="text" name="product_code" placeholder="Kode (PRD03)" required class="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs font-mono uppercase">
            <input type="number" name="berat_gram" placeholder="Berat (gram)" required class="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs">
          </div>
          <div class="flex gap-2">
            <input type="text" name="nama_produk" placeholder="Nama Produk..." required class="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs">
            <button type="submit" class="px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold cursor-pointer">Simpan</button>
          </div>
        </form>
      </div>
    </section>

    <!-- TABEL TRACEABILITY RIWAYAT SCAN -->
    <section class="bg-[#0f172a] border border-slate-800/90 rounded-2xl overflow-hidden shadow-sm">
      <div class="p-5 border-b border-slate-800/80 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h2 class="text-sm font-bold text-white uppercase tracking-wider">Audit Traceability Pemindaian</h2>
          <p class="text-xs text-slate-400 mt-0.5">Pencarian riwayat UID barcode, relasi batch/produk, kecepatan sabuk, dan ekspor laporan</p>
        </div>

        <form method="GET" action="{{ route('dashboard') }}" class="flex flex-wrap items-center gap-2">
          <input type="text" name="search" value="{{ request('search') }}" placeholder="Cari UID / Produk / Batch..."
                 class="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white w-48 sm:w-56 focus:outline-none focus:border-sky-500">

          <select name="batch_id" class="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white">
            <option value="">Semua Batch</option>
            @foreach($batches as $b)
              <option value="{{ $b->id }}" {{ request('batch_id') == $b->id ? 'selected' : '' }}>{{ $b->batch_code }}</option>
            @endforeach
          </select>

          <select name="status" class="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white">
            <option value="">Semua Status</option>
            <option value="VALID" {{ request('status') == 'VALID' ? 'selected' : '' }}>VALID</option>
            <option value="FAILED" {{ request('status') == 'FAILED' ? 'selected' : '' }}>FAILED (Alert)</option>
          </select>

          <button type="submit" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-white cursor-pointer">
            Cari
          </button>

          @if(request()->hasAny(['search', 'batch_id', 'status']) && (request('search') || request('batch_id') || request('status')))
            <a href="{{ route('dashboard') }}" class="px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-white">Reset</a>
          @endif

          <a href="{{ route('export.csv', request()->query()) }}"
             class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-lg shadow-indigo-600/20 transition">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            Export CSV
          </a>
        </form>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="bg-slate-900/90 text-slate-400 text-[11px] font-bold uppercase tracking-wider border-b border-slate-800">
              <th class="py-3.5 px-5">Waktu Scan</th>
              <th class="py-3.5 px-5">UID Barcode</th>
              <th class="py-3.5 px-5">Kode Batch</th>
              <th class="py-3.5 px-5">Nama Produk</th>
              <th class="py-3.5 px-5">Format</th>
              <th class="py-3.5 px-5">Kecepatan</th>
              <th class="py-3.5 px-5">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/70">
            @forelse($logs as $log)
              <tr class="hover:bg-slate-800/40 transition-colors">
                <td class="py-3.5 px-5 text-xs font-mono text-slate-400 whitespace-nowrap">{{ $log->waktu_scan?->format('d M Y, H:i:s') }}</td>
                <td class="py-3.5 px-5 font-mono font-bold text-xs text-white whitespace-nowrap">{{ $log->uid_barcode }}</td>
                <td class="py-3.5 px-5 text-xs font-mono text-slate-300">{{ $log->batch->batch_code ?? '-' }}</td>
                <td class="py-3.5 px-5 text-xs text-slate-200">{{ $log->product->nama_produk ?? 'Umum / Non-Master' }}</td>
                <td class="py-3.5 px-5 text-xs font-mono text-slate-400">{{ $log->tipe_kode }}</td>
                <td class="py-3.5 px-5 text-xs font-mono text-sky-400 whitespace-nowrap">{{ number_format($log->rpm_saat_scan, 1) }} RPM</td>
                <td class="py-3.5 px-5 whitespace-nowrap">
                  @if($log->status_scan === 'VALID')
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> VALID
                    </span>
                  @else
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                      <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> FAILED
                    </span>
                  @endif
                </td>
              </tr>
            @empty
              <tr>
                <td colspan="7" class="py-12 text-center text-slate-500 text-xs">
                  Belum ada riwayat pemindaian yang tercatat di database.
                </td>
              </tr>
            @endforelse
          </tbody>
        </table>
      </div>

      @if($logs->hasPages())
        <div class="p-4 border-t border-slate-800/80">
          {{ $logs->links() }}
        </div>
      @endif
    </section>
  </main>

  <script>
    // ================= 1. WEBSOCKET MQTT REAL-TIME =================
    const WS_URL = "{{ env('MQTT_WS_URL', 'ws://192.168.137.230:9001') }}";
    const client = mqtt.connect(WS_URL, {
      clientId: 'Laravel-Dash-' + Math.random().toString(16).substring(2, 8)
    });

    const badge = document.getElementById('mqtt-badge');
    const dot = document.getElementById('mqtt-dot');
    const text = document.getElementById('mqtt-text');

    client.on('connect', () => {
      badge.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
      dot.className = 'w-2 h-2 rounded-full bg-emerald-400';
      text.textContent = 'WebSocket Aktif (Raspberry Pi)';
      client.subscribe(['kel9_iot/conveyor/status', 'kel9_iot/conveyor/data']);
    });

    client.on('close', () => {
      badge.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30';
      dot.className = 'w-2 h-2 rounded-full bg-rose-500 animate-pulse';
      text.textContent = 'WebSocket Terputus';
    });

    client.on('message', (topic, message) => {
      try {
        const data = JSON.parse(message.toString());

        if (topic === 'kel9_iot/conveyor/status') {
          const stEl = document.getElementById('status-mesin');
          stEl.textContent = data.status;

          if (data.status === 'RUNNING') stEl.className = 'text-2xl font-bold font-mono mt-3 text-emerald-400';
          else if (data.status === 'SCANNING') stEl.className = 'text-2xl font-bold font-mono mt-3 text-amber-400';
          else stEl.className = 'text-2xl font-bold font-mono mt-3 text-rose-400';

          document.getElementById('status-detail').textContent = `Saklar: ${data.saklar} • Web: ${data.sistem}`;
          document.getElementById('live-rpm').textContent = Number(data.rpm).toFixed(1);
          document.getElementById('pid-detail').textContent = `Target: ${data.setpoint} RPM • PWM: ${data.pwm}`;
        }

        if (topic === 'kel9_iot/conveyor/data') {
          document.getElementById('last-uid').textContent = `Terakhir: ${data.uid_barcode}`;
          if (data.status_scan === 'VALID') {
            const el = document.getElementById('live-valid');
            el.textContent = parseInt(el.textContent || '0') + 1;
          } else {
            const el = document.getElementById('live-failed');
            el.textContent = parseInt(el.textContent || '0') + 1;
          }
          setTimeout(() => window.location.reload(), 900);
        }
      } catch (e) {}
    });

    function kirimPerintah(cmd) {
      client.publish('kel9_iot/conveyor/kontrol', cmd);
    }

    function ubahRPM() {
      const rpm = document.getElementById('input-rpm').value;
      if (rpm >= 20 && rpm <= 500) {
        client.publish('kel9_iot/conveyor/kontrol', 'RPM:' + rpm);
      }
    }

    function resetCounter() {
      if (confirm('Reset hitungan barang dan daftar anti-duplikat di konveyor?')) {
        client.publish('kel9_iot/conveyor/reset', 'RESET');
      }
    }

    // ================= 2. GENERATOR LABEL QR & CODE-128 =================
    function generateLabel() {
      const b = document.getElementById('gen-batch')?.value || 'BCH2611';
      const p = document.getElementById('gen-prod')?.value || 'PRD01';
      const s = (document.getElementById('gen-seq')?.value || '0001').trim();
      const uid = `${b}-${p}-${s}`;

      document.getElementById('uid-preview-text').textContent = uid;

      const qrBox = document.getElementById('qr-preview');
      qrBox.innerHTML = '';
      new QRCode(qrBox, { text: uid, width: 68, height: 68, correctLevel: QRCode.CorrectLevel.M });

      JsBarcode('#barcode-1d-preview', uid, {
        format: 'CODE128',
        width: 1.3,
        height: 32,
        displayValue: false,
        margin: 0
      });
    }

    function cetakLabel() {
      const uid = document.getElementById('uid-preview-text').textContent;
      const qrImg = document.querySelector('#qr-preview img')?.src || document.querySelector('#qr-preview canvas')?.toDataURL();
      const win = window.open('', '_blank', 'width=420,height=420');
      win.document.write(`
        <html><body style="font-family:monospace;text-align:center;padding:30px;">
          <div style="border:2px solid #000;padding:20px;display:inline-block;">
            <img src="${qrImg}" style="width:180px;height:180px;"/><br/>
            <strong style="font-size:16px;display:block;margin-top:10px;">${uid}</strong>
          </div>
          <script>window.onload = function(){ window.print(); }<\/script>
        </body></html>
      `);
      win.document.close();
    }

    generateLabel();

    // ================= 3. CHART.JS LAJU PRODUKSI =================
    const chartData = @json($chartRows);
    const labels = chartData.length ? chartData.map(r => r.jam) : ['Belum ada scan hari ini'];
    const validSeries = chartData.length ? chartData.map(r => r.valid_count) : [0];
    const failedSeries = chartData.length ? chartData.map(r => r.failed_count) : [0];

    new Chart(document.getElementById('productionChart'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Scan Valid',
            data: validSeries,
            backgroundColor: '#10b981',
            borderRadius: 6,
            barPercentage: 0.55
          },
          {
            label: 'Gagal Scan (No Barcode)',
            data: failedSeries,
            backgroundColor: '#f59e0b',
            borderRadius: 6,
            barPercentage: 0.55
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#cbd5e1', font: { family: 'Plus Jakarta Sans', size: 12 } } }
        },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#1e293b' } }
        }
      }
    });
  </script>
</body>
</html>