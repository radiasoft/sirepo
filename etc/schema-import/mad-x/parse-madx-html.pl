use strict;
use Data::Dumper;

#TODO(pjm): read field units

my($_COMMON_FIELDS) = ['APERTYPE', 'APERTURE', 'APER_OFFSET', 'APER_TOL'];

#TODO(pjm): lookup enums from model/field
my($_ENUMS) = {
    BeambeamBbshape => [
        ["1", "Gaussian"],
        ["2", "Trapezoidal"],
        ["3", "Hollow Parabolic"],
    ],
    BeambeamBbdir => [
        ["-1", "Beams move in opposite direction"],
        ["0", "Opposite beam does not move"],
        ["1", "Beams move in same direction"],
    ],
};

my($_BOOLEAN_VALUE) = {
    true => '"1"',
    false => '"0"',
};

my($_TYPES) = {
    'double value' => 'Float',
    string => 'String',
    logical => 'Boolean',
    integer => 'Integer',
    'double array' => 'FloatArray',
};

my($_MATRIX_FIELDS) = [
    map('KICK' . $_, (1 .. 6)),
    map({
        my($v) = $_;
        map({
            'RM' . $v . $_,
        } (1 .. 6));
    } 1 .. 6),
    map({
        my($v1) = $_;
        map({
            my($v2) = $_;
            map({
                'TM' . $v1 . $v2 . $_,
            } (1 .. 6));
        } (1 .. 6));
    } (1 .. 6)),
];

sub strip {
    my($v) = @_;
    $v =~ s/^\s*|\s*$//g;
    return $v;
}

sub parse_file {
    my($filename, $models) = @_;
    open(IN, $filename) || die($1);
    my($in_pre) = 0, 0;
    my($current) = '';
    foreach my $line (<IN>) {
        $line =~ s/[^[:print:]]+//g;
        $line =~ s/\!.*//;
        $line = strip($line);
        if ($line =~ s/^(.*?)<pre>//i) {
            #print('in pre' . "\n");
            $in_pre = 1;
        }
        if ($in_pre) {
            if ($line =~ /^\s*label\s*:\s*(.*)$/i) {
                #print('in label' . "\n");
                my($v) = $1;
                die() if $current;
                if ($v =~ /;/) {
                    push(@$models, $v);
                }
                else {
                    $current = $v;
                }
            }
            elsif ($current) {
                $current .= $line;
                if ($current =~ /\;/) {
                    push(@$models, $current);
                    $current = '';
                }
            }
        }
        if ($line =~ m,</pre>,i) {
            #print('out pre' . "\n");
            $in_pre = 0;
        }
    }
    die() if $current;
    close(IN);
    return;
}

sub parse_model {
    my($model) = @_;
    unless ($model =~ s/^(\w+)[,;]//) {
        #print('not model: ', $model, "\n");
        return;
    }
    my($name) = uc($1);
    #print($name, "\n");
    if ($model =~ /\.\.\./) {
        print('warning: ' . $name . ' contains ... fields' . "\n");
        print(' ' . $model . "\n");
    }
    my($fields) = [];
    foreach my $field ($model =~ /(\w+)\s*\:?=/g) {
        next if $name =~ /COLLIMATOR/ && $field =~ /SIZE/;
        next if $name =~ /BEND/ && $field eq 'K0';
        push(@$fields, uc($field));
    }
    return $name, $fields;
}

sub parse_models {
    my($res) = {};
    my($models) = @_;
    foreach my $model (@$models) {
        my($name, $fields) = parse_model($model);
        next unless $name;
        next if $name eq 'CLASS';
        $res->{$name} = $fields;
    }
    return $res;
}

sub lookup_madx_types {
    my($name, $fields) = @_;
    die() if system("echo 'help, $name;' | madx > tmp.txt");
    my($all_fields) = {};
    open(IN, 'tmp.txt') || die($!);
    foreach my $line (<IN>) {
        if ($line =~ /^parameter:\s*(\w+) (.*?):(.*?)$/) {
            my($f) = uc($1);
            my($type) = strip($2);
            my($default) = strip($3);
            $all_fields->{$f} = [$type, $default];
        }
    }
    close(IN);
    my($res) = [];
    my($visited) = {};
    if ($name eq 'MATRIX') {
        push(@$fields, @$_MATRIX_FIELDS);
    }
    #print($name, "\n");
    foreach my $f (@$fields) {
        next if $f eq 'TYPE';
        next if $visited->{$f};
        $visited->{$f} = 1;
        my($info) = $all_fields->{$f};
        die('missing field info: ' . $f)
            unless $info;
        #print(' ', $f, ' ', $info->[0], ' ', $info->[1], "\n");
        push(@$res, [$f, $info->[0], $info->[1]]);
    }
    foreach my $f (@$_COMMON_FIELDS) {
        next if $visited->{$f};
        if ($all_fields->{$f}) {
            my($info) = $all_fields->{$f};
            #print(' ', $f, ' ', $info->[0], ' ', $info->[1], "\n");
            push(@$res, [$f, $info->[0], $info->[1]]);
        }
    }
    return $res;
}

# missing from html doc, but present in elements.tex
my($models) = [
    'CHANGEREF, PATCH_ANG={real, real, real}, PATCH_TRANS={real, real, real};',
    'COLLIMATOR, L=real, APERTYPE=string, APERTURE={values}, APER_OFFSET={values}, APER_TOL={values};',
    'HACDIPOLE, L=real, VOLT=real,  FREQ=real, LAG=real, RAMP1=integer, RAMP2=integer, RAMP3=integer, RAMP4=integer;',
    'TRANSLATION, DX=real, DY=real, DS=real;',
    'TWCAVITY, L=real, VOLT=real, FREQ=real, LAG=real, PSI=real, DELTA_LAG=real;',
    'VACDIPOLE, L=real, VOLT=real,  FREQ=real, LAG=real, RAMP1=integer, RAMP2=integer, RAMP3=integer, RAMP4=integer;',
    'XROTATION,ANGLE=real;',
];

foreach my $f (</home/vagrant/src/MethodicalAcceleratorDesign/MAD-X/doc/usrguide/Introduction/*.html>) {
    #print($f, "\n");
    parse_file($f, $models);
}
my($info) = parse_models($models);

my($schema) = {};
foreach my $name (sort(keys(%$info))) {
    $schema->{$name} = lookup_madx_types($name, $info->{$name});
}

foreach my $name (sort(keys(%$schema))) {
    print($name, "\n");
    foreach my $field (@{$schema->{$name}}) {
        my($type) = $field->[1];
        unless ($_TYPES->{$type}) {
            print('unknown type: ' . $type . "\n");
            next;
        }
        $field->[0] = lc($field->[0]);
        $field->[1] = $_TYPES->{$type};
        $field->[2] =~ s/\b0\.000000e\+00\b/0/g;
        if ($field->[1] eq 'Boolean') {
            $field->[2] = $_BOOLEAN_VALUE->{$field->[2]} || die();
        }
    }
}

# use Data::Dumper;
# print(Dumper($schema));

foreach my $name (sort(keys(%$schema))) {
    my($res) = '        "' . $name . '": {' . "\n";
    foreach my $field (@{$schema->{$name}}) {
        my($default) = $field->[2];
        if ($field->[1] eq 'String' || $field->[1] eq 'FloatArray') {
            $default = '"' . $default . '"';
        }
        $res .= '            "' . $field->[0]
            . '": ["' . uc($field->[0]) . '", "' . $field->[1]
            . '", ' . $default . '],' . "\n";
    }
    $res =~ s/,$//;
    $res .= '        },' . "\n";
    print($res);
}
