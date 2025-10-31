#!/usr/bin/env perl
use strict;
use warnings;
use Getopt::Long qw(GetOptions);
use JSON::PP qw(decode_json encode_json);
use LWP::UserAgent;
use URI::Escape qw(uri_escape);

my %opt = (
    season        => '2023-24',
    season_type   => 'Regular Season',
    min_poss      => 100,
    league        => 'nba',
    weights       => 'pg:100,sg:20,sf:100,pf:50,c:100',
);

GetOptions(
    'season=s'       => \$opt{season},
    'season-type=s'  => \$opt{season_type},
    'min-poss=i'     => \$opt{min_poss},
    'league=s'       => \$opt{league},
    'weights=s'      => \$opt{weights},
) or die "Usage: $0 team1_id lineup1_id team2_id lineup2_id [options]\n";

@ARGV == 4 or die "Usage: $0 team1_id lineup1_id team2_id lineup2_id [options]\n";

my ($team1, $lineup1, $team2, $lineup2) = @ARGV;

my %weights = (
    pg => 100,
    sg => 20,
    sf => 100,
    pf => 50,
    c  => 100,
);

if (defined $opt{weights}) {
    for my $pair (split /,/ => $opt{weights}) {
        my ($slot, $value) = split /:/ => $pair;
        next unless defined $slot && defined $value;
        $weights{lc $slot} = $value + 0;
    }
}

my $ua = LWP::UserAgent->new(timeout => 20);

my $data1 = fetch_lineup($ua, $team1, $lineup1);
my $data2 = fetch_lineup($ua, $team2, $lineup2);

my $metrics1 = compute_metrics($data1);
my $metrics2 = compute_metrics($data2);

my $baseline = $metrics1->{net} - $metrics2->{net};

my %slots = (
    pg => ($metrics2->{tov_rate} - $metrics1->{tov_rate}) * $weights{pg},
    sg => ($metrics1->{three_par} - $metrics2->{three_par}) * $weights{sg},
    sf => ($metrics1->{efg} - $metrics2->{efg}) * $weights{sf},
    pf => ($metrics1->{rim_acc} - $metrics2->{rim_acc}) * $weights{pf},
    c  => ($metrics1->{second_chance} - $metrics2->{second_chance}) * $weights{c},
);

my $slot_total = 0;
$slot_total += $_ for values %slots;

my $delta = $baseline + $slot_total;

print encode_json({
    inputs => {
        season        => $opt{season},
        season_type   => $opt{season_type},
        min_poss      => $opt{min_poss},
        weights       => \%weights,
        team1         => { id => $team1, lineup => $lineup1 },
        team2         => { id => $team2, lineup => $lineup2 },
    },
    lineup_a => format_output($data1, $metrics1),
    lineup_b => format_output($data2, $metrics2),
    baseline_delta => $baseline,
    slot_adjustments => \%slots,
    final_delta => $delta,
}) . "\n";

exit 0;

sub fetch_lineup {
    my ($ua, $team_id, $lineup_id) = @_;

    my $url = sprintf 'https://api.pbpstats.com/get-totals/%s?Type=Lineup&Season=%s&SeasonType=%s&TeamId=%s&Table=Scoring&MinimumPossessions=%d',
        uri_escape($opt{league}), uri_escape($opt{season}), uri_escape($opt{season_type}), uri_escape($team_id), $opt{min_poss};

    my $res = $ua->get($url);
    $res->is_success or die "Failed to fetch data for team $team_id: " . $res->status_line . "\n";

    my $json = decode_json($res->decoded_content);
    my ($row) = grep { $_->{EntityId} eq $lineup_id } @{ $json->{multi_row_table_data} || [] };

    $row or die "Lineup $lineup_id not found for team $team_id.\n";

    return $row;
}

sub compute_metrics {
    my ($row) = @_;

    my $off = $row->{Points} / $row->{OffPoss} * 100;
    my $def = $row->{OpponentPoints} / $row->{DefPoss} * 100;

    return {
        off             => $off,
        def             => $def,
        net             => $off - $def,
        tov_rate        => $row->{Turnovers} / $row->{OffPoss},
        three_par       => $row->{FG3APct},
        efg             => $row->{EfgPct},
        rim_acc         => $row->{AtRimAccuracy},
        second_chance   => $row->{SecondChancePointsPct},
        possessions_off => $row->{OffPoss},
        possessions_def => $row->{DefPoss},
        minutes         => $row->{SecondsPlayed} / 60,
    };
}

sub format_output {
    my ($row, $metrics) = @_;

    return {
        name       => $row->{Name},
        entity_id  => $row->{EntityId},
        off_rating => $metrics->{off},
        def_rating => $metrics->{def},
        net_rating => $metrics->{net},
        metrics    => {
            tov_rate      => $metrics->{tov_rate},
            three_par     => $metrics->{three_par},
            efg           => $metrics->{efg},
            rim_accuracy  => $metrics->{rim_acc},
            second_chance => $metrics->{second_chance},
        },
        samples => {
            possessions_off => $metrics->{possessions_off},
            possessions_def => $metrics->{possessions_def},
            minutes         => $metrics->{minutes},
        },
    };
}
