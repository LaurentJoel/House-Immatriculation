#!/usr/bin/perl
# Find a row with the maximum non-null values
my $best_count = 0;
my $best_line = "";
my $line_num = 0;
open(F, '/tmp/bck_houses_immat') or die "Cannot open: $!";
while (my $line = <F>) {
    $line_num++;
    chomp $line;
    my @cols = split(/\t/, $line);
    my $count = 0;
    for my $c (@cols) {
        $count++ if $c ne "\\N" && $c ne "";
    }
    if ($count > $best_count) {
        $best_count = $count;
        $best_line = $line;
        print "Line $line_num has $count non-null cols\n";
    }
    last if $line_num > 50000;
}
close(F);
print "\n--- Best row ($best_count non-null cols) ---\n";
my @cols = split(/\t/, $best_line);
for my $i (0 .. $#cols) {
    my $val = substr($cols[$i], 0, 80);
    print "col$i: [$val]\n";
}
