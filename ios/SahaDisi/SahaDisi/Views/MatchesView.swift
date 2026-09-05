import SwiftUI

struct MatchesView: View {
    @EnvironmentObject var store: AppStore
    @State private var selectedWeek: Int?

    private var matches: [Match] { (store.payload?.matches ?? []).sorted { ($0.week, $0.kickoff) < ($1.week, $1.kickoff) } }
    private var weeks: [Int] { Array(Set(matches.map(\.week))).sorted() }
    private var currentWeek: Int? {
        let now = Date()
        let dated = matches.compactMap { match -> (Int, Date)? in
            guard let date = parseDate(match.kickoff) else { return nil }
            return (match.week, date)
        }
        if let nearest = dated.min(by: { abs($0.1.timeIntervalSince(now)) < abs($1.1.timeIntervalSince(now)) }) { return nearest.0 }
        let withScores = matches.filter { $0.homeScore != nil && $0.awayScore != nil }.map(\.week)
        return withScores.max() ?? weeks.first
    }
    private var visibleMatches: [Match] {
        guard let selectedWeek else { return matches }
        return matches.filter { $0.week == selectedWeek }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                HStack { Text("Maçlar").font(.largeTitle.black()); Spacer(); TagPill(text: "TFF fikstürü") }
                if let generatedAt = store.payload?.generatedAt {
                    Text("Veri güncellemesi: \(SDDate.text(generatedAt, includeTime: true))").font(.caption2).foregroundStyle(SDTheme.muted)
                }
                Text("Trendyol Süper Lig fikstürü · haftalar ve güncel skorlar").font(.subheadline).foregroundStyle(SDTheme.muted)
                weekPicker

                if visibleMatches.isEmpty {
                    ContentUnavailableView("Maç bulunamadı", systemImage: "sportscourt", description: Text("Canlı fikstür güncelleniyor. Yenilemek için aşağı çek."))
                } else {
                    ForEach(weeksToShow, id: \.self) { week in
                        VStack(alignment: .leading, spacing: 10) {
                            Text(weekTitle(week)).font(.title3.bold()).padding(.top, 4)
                            ForEach(sortedMatches(in: week)) { match in matchCard(match) }
                        }
                    }
                }
            }.padding(16)
        }
        .background(SDTheme.background)
        .toolbar(.hidden, for: .navigationBar)
        .refreshable { await store.refresh() }
        .onAppear { if selectedWeek == nil { selectedWeek = currentWeek } }
    }

    private var weeksToShow: [Int] { selectedWeek.map { [$0] } ?? weeks }

    private func sortedMatches(in week: Int) -> [Match] {
        visibleMatches.filter { $0.week == week }.sorted {
            let l = store.statements(matchID: $0.id).count
            let r = store.statements(matchID: $1.id).count
            if l != r { return l > r }
            return $0.kickoff < $1.kickoff
        }
    }

    private var weekPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Button { selectedWeek = nil } label: { weekChip("Tüm Haftalar", active: selectedWeek == nil) }.buttonStyle(.plain)
                ForEach(weeks, id: \.self) { week in
                    Button { selectedWeek = week } label: { weekChip(weekTitle(week), active: selectedWeek == week) }.buttonStyle(.plain)
                }
            }
        }
    }

    private func weekChip(_ text: String, active: Bool) -> some View {
        Text(text).font(.caption.bold()).padding(.horizontal, 13).padding(.vertical, 8)
            .foregroundStyle(active ? Color.black : SDTheme.muted)
            .background(active ? Color.white : SDTheme.panel).clipShape(Capsule())
    }

    private func matchCard(_ match: Match) -> some View {
        let linked = store.statements(matchID: match.id)
        return NavigationLink { MatchDetailView(match: match) } label: {
            VStack(spacing: 0) {
                MatchPoster(match: match, compact: true).frame(height: 112)
                VStack(spacing: 10) {
                    HStack {
                        Text(SDDate.text(match.kickoff, includeTime: true)).font(.caption2).foregroundStyle(SDTheme.muted2)
                        Spacer(); Text(weekTitle(match.week)).font(.caption2.bold()).foregroundStyle(SDTheme.muted)
                    }
                    HStack {
                        Text(match.home).font(.headline).frame(maxWidth: .infinity, alignment: .leading)
                        Text(score(match)).font(.title3.black()).frame(minWidth: 60)
                        Text(match.away).font(.headline).frame(maxWidth: .infinity, alignment: .trailing)
                    }
                    Text(match.statusText).font(.caption).foregroundStyle(SDTheme.muted)
                    HStack {
                        Text(linked.isEmpty ? "Henüz bu maça bağlı doğrulanmış yorum yok" : "\(linked.count) maça bağlı doğrulanmış yorum")
                            .font(.caption2).foregroundStyle(linked.isEmpty ? SDTheme.muted2 : SDTheme.accent)
                        Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                    }
                }.padding(14)
            }
            .background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 17)).overlay(RoundedRectangle(cornerRadius: 17).stroke(SDTheme.line))
        }.buttonStyle(.plain)
    }

    private func weekTitle(_ week: Int) -> String {
        let words = [1:"Birinci Hafta",2:"İkinci Hafta",3:"Üçüncü Hafta",4:"Dördüncü Hafta",5:"Beşinci Hafta",6:"Altıncı Hafta",7:"Yedinci Hafta",8:"Sekizinci Hafta",9:"Dokuzuncu Hafta",10:"Onuncu Hafta",11:"On Birinci Hafta",12:"On İkinci Hafta",13:"On Üçüncü Hafta",14:"On Dördüncü Hafta",15:"On Beşinci Hafta",16:"On Altıncı Hafta",17:"On Yedinci Hafta",18:"On Sekizinci Hafta",19:"On Dokuzuncu Hafta",20:"Yirminci Hafta",21:"Yirmi Birinci Hafta",22:"Yirmi İkinci Hafta",23:"Yirmi Üçüncü Hafta",24:"Yirmi Dördüncü Hafta",25:"Yirmi Beşinci Hafta",26:"Yirmi Altıncı Hafta",27:"Yirmi Yedinci Hafta",28:"Yirmi Sekizinci Hafta",29:"Yirmi Dokuzuncu Hafta",30:"Otuzuncu Hafta",31:"Otuz Birinci Hafta",32:"Otuz İkinci Hafta",33:"Otuz Üçüncü Hafta",34:"Otuz Dördüncü Hafta"]
        return words[week] ?? "\(week). Hafta"
    }

    private func parseDate(_ value: String) -> Date? {
        let iso = ISO8601DateFormatter()
        if let d = iso.date(from: value) { return d }
        let formats = ["yyyy-MM-dd", "dd.MM.yyyy HH:mm"]
        for format in formats {
            let formatter = DateFormatter(); formatter.locale = Locale(identifier: "tr_TR"); formatter.timeZone = TimeZone(identifier: "Europe/Istanbul"); formatter.dateFormat = format
            if let d = formatter.date(from: value) { return d }
        }
        return nil
    }

    private func score(_ m: Match) -> String { m.scoreText }
}

struct MatchPoster: View {
    let match: Match
    var compact = false
    var body: some View {
        ZStack {
            LinearGradient(colors: [SDTheme.panel2, SDTheme.background], startPoint: .topLeading, endPoint: .bottomTrailing)
            Circle().fill(Color.white.opacity(0.035)).frame(width: 220, height: 220).offset(x: -110, y: -70)
            Circle().fill(Color.white.opacity(0.025)).frame(width: 180, height: 180).offset(x: 130, y: 80)
            HStack(spacing: compact ? 18 : 28) {
                TeamLogoView(name: match.home, urlString: match.homeLogoURL, size: compact ? 62 : 82)
                VStack(spacing: 4) {
                    Text(match.scoreText)
                        .font(.system(size: compact ? 18 : 26, weight: .black, design: .rounded))
                    Text("SÜPER LİG").font(.system(size: 9, weight: .bold)).tracking(1.2).foregroundStyle(SDTheme.muted2)
                }
                TeamLogoView(name: match.away, urlString: match.awayLogoURL, size: compact ? 62 : 82)
            }
        }.clipped()
    }
}
