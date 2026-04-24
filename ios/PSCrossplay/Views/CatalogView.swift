import SwiftUI

struct CatalogView: View {
    @EnvironmentObject var store: GameStore
    @Binding var filters: FilterState

    private var allGenres: [String] {
        Array(Set(store.games.flatMap { $0.genres })).sorted()
    }
    private var allViews: [String] {
        let order = ["First-Person", "Third-Person", "Top-Down/Isometric", "Side-Scroller/2D", "Fixed Camera", "VR"]
        let present = Set(store.games.flatMap { $0.viewTypes })
        return order.filter { present.contains($0) }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                FilterBar(filters: $filters, allGenres: allGenres, allViews: allViews)
                    .padding(.horizontal)
                    .padding(.top, 8)

                Text("\(store.games.count) total crossplay titles")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)

                group(title: "In PlayStation Plus Extra") {
                    SectionView(title: "PS4 ↔ PS5", games: filteredExtraPS4PS5, filters: filters)
                    SectionView(title: "PS5 ↔ PC", games: filteredExtraPS5PC, filters: filters)
                    SectionView(title: "PS4 ↔ PS5 ↔ PC", games: filteredExtraTriple, filters: filters)
                }
                group(title: "All games (free or paid)") {
                    SectionView(title: "PS5 ↔ PC", games: filteredAllPS5PC, filters: filters)
                    SectionView(title: "PS4 ↔ PS5 ↔ PC", games: filteredAllTriple, filters: filters)
                }
            }
            .padding(.bottom, 40)
        }
        .refreshable { await store.reloadFromServer() }
    }

    @ViewBuilder
    private func group<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        Text(title)
            .font(.title3.weight(.semibold))
            .foregroundStyle(.tint)
            .padding(.horizontal)
            .padding(.top, 14)
        content()
    }

    // MARK: - filtering

    private func pass(_ g: Game) -> Bool {
        if filters.strictOnly && g.confidence != "high" { return false }
        if !filters.search.isEmpty && !g.title.localizedCaseInsensitiveContains(filters.search) { return false }
        if !filters.genre.isEmpty && !g.genres.contains(filters.genre) { return false }
        if !filters.view.isEmpty && !g.viewTypes.contains(filters.view) { return false }
        return true
    }

    private var filteredExtraPS4PS5: [Game] { store.extraPS4PS5.filter(pass).sorted { $0.title < $1.title } }
    private var filteredExtraPS5PC: [Game] { store.extraPS5PC.filter(pass).sorted { $0.title < $1.title } }
    private var filteredExtraTriple: [Game] { store.extraAll.filter(pass).sorted { $0.title < $1.title } }
    private var filteredAllPS5PC: [Game] { store.allPS5PC.filter(pass).sorted { $0.title < $1.title } }
    private var filteredAllTriple: [Game] { store.allTriple.filter(pass).sorted { $0.title < $1.title } }
}
