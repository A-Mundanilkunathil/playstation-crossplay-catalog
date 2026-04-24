import SwiftUI

struct SectionView: View {
    let title: String
    let games: [Game]
    let filters: FilterState

    private let columns = [GridItem(.adaptive(minimum: 150), spacing: 12)]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(title).font(.headline)
                Text("(\(games.count))").font(.subheadline).foregroundStyle(.secondary)
                Spacer()
            }
            .padding(.horizontal)

            if games.isEmpty {
                Text("No games match your filters.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
                    .padding(.vertical, 8)
            } else {
                LazyVGrid(columns: columns, spacing: 12) {
                    ForEach(games) { g in
                        GameCard(game: g, showLabels: filters.showLabels)
                    }
                }
                .padding(.horizontal)
            }

            Divider().padding(.horizontal).padding(.top, 4)
        }
    }
}
