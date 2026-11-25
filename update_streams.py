import requests
import re
import sys
from datetime import datetime

OUTPUT_FILE = "index.m3u"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}


def fetch_url(url, timeout=30):
    """Download konten dari URL dengan error handling."""
    try:
        print(f"  -> Mengunduh: {url}")
        res = requests.get(url, headers=HEADERS, timeout=timeout)
        res.raise_for_status()
        return res.text
    except requests.exceptions.RequestException as e:
        print(f"  [!] GAGAL download {url}: {e}")
        return None


def parse_m3u(content, source_name):
    """Parsing konten M3U menjadi list channel."""
    channels = []
    lines = content.splitlines()
    current_meta = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('#EXTM3U'):
            continue

        if line.startswith('#'):
            current_meta.append(line)
        else:
            if current_meta:
                extinf_line = next(
                    (l for l in current_meta if l.startswith('#EXTINF')), None
                )
                if extinf_line:
                    title_match = re.search(r',\s*(.+)$', extinf_line)
                    title = title_match.group(1).strip() if title_match else "Unknown"

                    group_match = re.search(r'group-title="([^"]*)"', extinf_line)
                    group = group_match.group(1) if group_match else "Uncategorized"

                    logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
                    logo = logo_match.group(1) if logo_match else ""

                    channels.append({
                        'title': title,
                        'group': group,
                        'logo': logo,
                        'meta_lines': current_meta,
                        'url': line,
                        'source': source_name
                    })
            current_meta = []

    return channels


def main():
    all_channels = []

    # =====================================================
    # SUMBER 1: dhanytv (sudah include banyak channel lokal)
    # =====================================================
    print("\n[1/3] Memproses dhanytv...")
    dhanytv_url = "https://raw.githubusercontent.com/dhasap/dhanytv/main/dhanytv.m3u"
    dhanytv_content = fetch_url(dhanytv_url)
    if dhanytv_content:
        channels = parse_m3u(dhanytv_content, "dhanytv")
        all_channels.extend(channels)
        print(f"  [OK] {len(channels)} channel dari dhanytv")

    # =====================================================
    # SUMBER 2: iptv-org Indonesia
    # =====================================================
    print("\n[2/3] Memproses iptv-org Indonesia...")
    iptv_org_url = "https://iptv-org.github.io/iptv/countries/id.m3u"
    iptv_org_content = fetch_url(iptv_org_url)
    if iptv_org_content:
        channels = parse_m3u(iptv_org_content, "iptv-org")
        all_channels.extend(channels)
        print(f"  [OK] {len(channels)} channel dari iptv-org")

    # =====================================================
    # SUMBER 3: dens.tv (scrape langsung dari halaman)
    # =====================================================
    print("\n[3/3] Memproses dens.tv...")
    dens_content = fetch_url("https://www.dens.tv/tv-local")
    dens_count = 0
    if dens_content:
        m3u8_matches = re.findall(r'https?://[^"\'<>\s]+\.m3u8', dens_content)
        seen_dens_urls = set()
        for url in m3u8_matches:
            if url not in seen_dens_urls:
                seen_dens_urls.add(url)
                all_channels.append({
                    'title': 'Dens TV Local',
                    'group': 'Dens TV',
                    'logo': 'https://www.dens.tv/images/logo.png',
                    'meta_lines': [
                        f'#EXTINF:-1 group-title="Dens TV" tvg-logo="https://www.dens.tv/images/logo.png", Dens TV Local'
                    ],
                    'url': url,
                    'source': 'dens.tv'
                })
                dens_count += 1
        print(f"  [OK] {dens_count} stream dari dens.tv")

    # =====================================================
    # DEDUPLIKASI (hapus URL yang sama)
    # =====================================================
    print("\n[*] Menghapus duplikat URL...")
    unique_channels = []
    seen_urls = set()
    for ch in all_channels:
        url = ch['url'].strip()
        if url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(ch)

    # =====================================================
    # SORTIR berdasarkan grup lalu nama channel
    # =====================================================
    unique_channels.sort(key=lambda x: (x['group'].lower(), x['title'].lower()))

    # =====================================================
    # SIMPAN ke index.m3u
    # =====================================================
    print(f"[*] Menyimpan ke {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U url-tvg="https://iptv-org.github.io/epg/guides/id/vidio.com.epg.xml,https://iptv-org.github.io/epg/guides/id/mncvision.id.epg.xml"\n')
        f.write(f'# Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC\n')
        for ch in unique_channels:
            for meta in ch['meta_lines']:
                f.write(f"{meta}\n")
            f.write(f"{ch['url']}\n")

    print(f"\n[SELESAI] {len(unique_channels)} channel unik berhasil disimpan ke {OUTPUT_FILE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
