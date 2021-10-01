use strict;

use Data::Dumper;

my($_ENUM_DEFAULT) = {
    WakeForm => 'ROUND',
    CyclotronCyclotrontype => 'PSI',
    DistributionEmissionmodel => 'NONE',
};
my($enums) = {
    AttlistValue => [
        ["ACTUAL", "ACTUAL"],
        ["IDEAL", "IDEAL"],
        ["ERROR", "ERROR"]
    ],
    BeamParticle => [
        ["", "NOT SELECTED"],
        ["POSITRON", "POSITRON"],
        ["ELECTRON", "ELECTRON"],
        ["PROTON", "PROTON"],
        ["ANTIPROTON", "ANTIPROTON"],
        ["HMINUS", "HMINUS"],
        ["CARBON", "CARBON"],
        ["URANIUM", "URANIUM"],
        ["MUON", "MUON"],
        ["DEUTERON", "DEUTERON"],
        ["XENON", "XENON"],
        ["OTHER", "OTHER"],
    ],
    MonitorMonitor_type => [
        ["", "NOT SELECTED"],
        ["TEMPORAL", "TEMPORAL"],
        ["SPATIAL", "SPATIAL"],
    ],
    RfcavityRfcavity_type => [
        ["", "NOT SELECTED"],
        ["STANDING", "STANDING"],
        ["SINGLEGAP", "SINGLEGAP"],
    ],
    CyclotronCyclotron_type => [
        ["", "NOT SELECTED"],
        ["CARBONCYCL", "CARBONCYCL"],
        ["CYCIAE", "CYCIAE"],
        ["AVFEQ", "AVFEQ"],
        ["FFAG", "FFA"],
        ["BANDRF", "BANDRF"],
        ["PSI", "PSI"],
    ],
    DistributionEmissionmodel => [
        ["NONE", "NONE"],
        ["ASTRA", "ASTRA"],
        ["NONEQUIL", "NONEQUIL"],
    ],
    DistributionInputmounits => [
        ["", "NOT SELECTED"],
        ["EV", "EV"],
        ["NONE", "NONE"],
    ],
    DistributionType => [
        ["", "NOT SELECTED"],
        ["FROMFILE", "FROMFILE"],
        ["GAUSS", "GAUSS"],
        ["BINOMIAL", "BINOMIAL"],
        ["FLATTOP", "FLATTOP"],
        ["GUNGAUSSFLATTOPTH", "GUNGAUSSFLATTOPTH"],
        ["ASTRAFLATTOPTH", "ASTRAFLATTOPTH"],
        ["GAUSSMATCHED", "GAUSSMATCHED"],
    ],
    FieldsolverFstype => [
        ["", "NOT SELECTED"],
        ["FFT", "FFT"],
        ["FFTPERIODIC", "FFTPERIODIC"],
        ["SAAMG", "SAAMG"],
        ["NONE", "NONE"]
    ],
    FieldsolverBcfftx => [
        ["OPEN", "OPEN"],
        ["DIRICHLET", "DIRICHLET (box)"],
        ["PERIODIC", "PERIODIC"],
    ],
    FieldsolverBcffty => [
        ["OPEN", "OPEN"],
        ["DIRICHLET", "DIRICHLET (box)"],
        ["PERIODIC", "PERIODIC"],
    ],
    FieldsolverBcfftz => [
        ["OPEN", "OPEN"],
        ["PERIODIC", "PERIODIC"],
    ],
    FieldsolverBcfftt => [
        ["OPEN", "OPEN"],
        ["PERIODIC", "PERIODIC"],
    ],
    FieldsolverGreensf => [
        ["STANDARD", "STANDARD"],
        ["INTEGRATED", "INTEGRATED"],
    ],
    FieldsolverItsolver => [
        ["CG", "CG"],
        ["BiCGSTAB", "BiCGSTAB"],
        ["GMRES", "GMRES"],
    ],
    FieldsolverInterpl => [
        ["CONSTANT", "CONSTANT"],
        ["LINEAR", "LINEAR"],
        ["QUADRATIC", "QUADRATIC"],
    ],
    FieldsolverPrecmode => [
        ["STD", "STD"],
        ["HIERARCHY", "HIERARCHY"],
        ["REUSE", "REUSE"],
    ],
    FilterType => [
        ["", "NOT SELECTED"],
        ["Savitzky-Golay", "Savitzky-Golay"],
        ["fixedFFTLowPass", "fixedFFTLowPass"],
        ["relativeFFTLowPass", "relativeFFTLowPass"],
        ["Stencil", "Stencil"],
    ],
    GeometryTopo => [
        ["BOX", "BOX"],
        ["BOXCORNER", "BOXCORNER"],
        ["ELLIPTIC", "ELLIPTIC"],
    ],
    MicadoMethod => [
        ["THICK", "THICK"],
        ["THIN", "THIN"],
        ["LINEAR", "LINEAR"],
    ],
    MicadoPlane => [
        ["X", "X"],
        ["Y", "Y"],
        ["BOTH", "BOTH"],
    ],
    OptionRngtype => [
        ["RANDOM", "RANDOM"],
        ["HALTON", "HALTON"],
        ["SOBOL", "SOBOL"],
        ["NINIEDERREITER", "NIEDERREITER (Gsl ref manual 18.5)"],
    ],
    OptionPsdumpframe => [
        ["GLOBAL", "GLOBAL"],
        ["BUNCH_MEAN", "BUNCH_MEAN"],
        ["REFERENCE", "REFERENCE"],
    ],
    ParticlematterinteractionMaterial => [
        ["", "NOT SELECTED"],
        ["Air", "Air"],
        ["AluminaAL2O3", "AluminaAL2O3"],
        ["Aluminum", "Aluminum"],
        ["Beryllium", "Beryllium"],
        ["BoronCarbide", "BoronCarbide"],
        ["Copper", "Copper"],
        ["Gold", "Gold"],
        ["Graphite", "Graphite"],
        ["GraphiteR6710", "GraphiteR6710"],
        ["Kapton", "Kapton"],
        ["Molybdenum", "Molybdenum"],
        ["Mylar", "Mylar"],
        ["Titanium", "Titanium"],
        ["Titan", "Titan"],
        ["Water", "Water"],
    ],
    ParticlematterinteractionType => [
        ["", "NOT SELECTED"],
        ["CCOLLIMATOR", "CCOLLIMATOR"],
        ["COLLIMATOR", "COLLIMATOR"],
        ["DEGRADER", "DEGRADER"],
    ],
    RunMbmode => [
        ["FORCE", "FORCE"],
        ["AUTO", "AUTO"],
    ],
    RunMethod => [
        ["THIN", "THIN"],
        ["THICK", "THICK"],
        ["OPAL-T", "OPAL-T"],
        ["OPAL-CYCL", "OPAL-CYCL"],
        ["PARALLEL-T", "PARALLEL-T"],
        ["CYCLOTRON-T", "CYCLOTRON-T"],
    ],
    RunMb_binning => [
        ["GAMMA", "GAMMA"],
        ["BATCH", "BATCH"],
    ],
    TrackTimeintegrator => [
        ["RK-4", "RK-4"],
        ["LF-2", "LF-2"],
        ["MTS", "MTS"],
    ],
    TwissMethod => [
        ["LINEAR", "LINEAR"],
        ["THIN", "THIN"],
        ["THICK", "THICK"],
        ["TRANSPORT", "TRANSPORT"],
    ],
    WakeType => [
        ["", "NOT SELECTED"],
        ["1D-CSR", "1D-CSR"],
        ["1D-CSR-IGF", "1D-CSR-IGF"],
        ["LONG-SHORT-RANGE", "LONG-SHORT-RANGE"],
        ["TRANSV-SHORT-RANGE", "TRANSV-SHORT-RANGE"],
        ["LONG-TRANSV-SHORT-RANGE", "LONG-TRANSV-SHORT-RANGE"],
    ],
    WakeConduct => [
        ["", "NOT SELECTED"],
        ["AC", "AC"],
        ["DC", "DC"],
    ],
    WakeForm => [
        ["ROUND", "ROUND"],
    ],
};

my($type_map) = {
    makeReal => 'RPNValue',
    makeBool => 'Boolean',
    makeBoolArray => 'OptionalString',
    makeString => 'OptionalString',
    makeRealArray => 'RPNValue',
    makeStringArray => 'OptionalString',
    makeTokenListArray => 'OptionalString',
    makeRange => 'OptionalString',
    makeTableRow => 'OptionalString',
};

sub clean_text {
    my($text) = @_;
    $text =~ s/^\s+|\s$//g;
    $text =~ s/""//g;
    $text =~ s/",\s*"$//g;
    $text =~ s/[,;.] (its|the)?\s*default value(s)? is .*//i;
    $text =~ s/\. default\s*[:=] .*//i;
    $text =~ s/\. default \S+$//i;
    return $text;
}

sub parse_file {
    my($filename) = @_;
    my($class) = $filename =~ /\/(\w+)\.cpp/;
    die($filename) unless $class;
    my($res) = {
        class => $class,
        description => '',
        fields => [],
    };
    open(IN, $filename) || die($!);
    my($prevline) = '';
    my($state) = ($class eq 'OpalElement' || $class eq 'Twiss') ? 'attr1' : 'class';
    while (defined(my $line = <IN>)) {
        if ($state eq 'class' && $line =~ /${class}\:\:${class}\(/) {
            $state = 'type';
            next;
        }
        $line =~ s/\\\"//g;
        # OpalElement(SIZE, "RBEND3D", "The \"RBEND3D\" element defines an RBEND with 3D field maps"),
        if ($state eq 'type' && $line =~ /\(?\s*(?:.*::)?(?:SIZE|COMMON), "(\w+)"(?:,\s*"(.*?)"\))?/) {
            my($type, $desc) = ($1, $2);
            $res->{type} = $1;
            if (length($desc)) {
                $res->{description} = $desc;
                $state = 'attr1';
            }
            else {
                $state = 'description';
            }
            next;
        }
        if ($state eq 'type' && $line =~ /\((?:SIZE|COMMON),/) {
            $state = 'attr1';
            next;
        }
        if ($state eq 'type' && $line =~ /OpalBend\("/) {
            $state = 'description';
            next;
        }
        if ($state eq 'description') {
            if ($line =~ /^\s+"(.*?)"/) {
                $res->{description} .= $1;
                $res->{description} =~ s/\\n/ /g;
                $res->{description} =~ s/\\//g;
                if ($line =~ /\)/) {
                    $state = 'attr1';
                }
                next
            }
            $res->{description} = '';
            $state = 'attr1';
            # fall through
        }
        # itsAttr[XSTART] = Attributes::makeReal
        # itsAttr[Attrib::Distribution::TYPE]
        if ($state eq 'attr1' && $line =~ /^\s+itsAttr\[[^\]]*?([A-Z0-9]+)\]\s*=.*?\:\:(\w+)/) {
            $prevline = $line;
            $state = 'attr2';
            unless ($line =~ /\;/) {
                next;
            }
            # all on one line
            $prevline = '';
        }
        if ($state eq 'attr1' && $line =~ /^\s+itsAttr\[[^\]]*?([A-Z0-9]+)\]/) {
            $prevline = $line;
            $state = 'attr2';
            unless ($line =~ /\;/) {
                next;
            }
            # all on one line
            $prevline = '';
        }
        if ($state eq 'attr2') {
            $line = $prevline . $line;
            $line =~ s/\n\s+//;
            unless ($line =~ /\;\s*$/) {
                $prevline = $line;
                next;
            }
            unless ($line =~ /itsAttr\[.*?\]\s*=/) {
                $state = 'attr1';
                next;
            }
            die('attr2 parse failed: ' . $class . ' ' . $line)
                unless $line =~ /itsAttr\[[^\]]*?([A-Z0-9]+)\]\s*=.*?\:\:(\w+)\("(\w+)",\s*"(.*?)"(?:\,\s*(.*?))?\)\;/;
            my($name1, $type, $name, $desc, $default) = ($1, $2, $3, $4, $5);
            if ($default) {
                $default =~ s/"//g;
                if (uc($default) eq 'NONE') {
                    $default = '';
                }
            }
            die($state . ' ' . $class . ' ' . $line) if $desc =~ /Attribute/;
            push(@{$res->{fields}}, {
                name => $name,
                type => $type,
                description => clean_text($desc),
                length($default) ? (default => $default) : (),
            });
            # warn($class . ' attr1 name != attr2 name: ' . $name1 . ' != ' . $name)
            #     unless $name1 eq $name;
            $state = 'attr1';
            next;
        }
        if ($state eq 'attr1' && $line =~ /^\s+register.*?Attribute/) {
            last;
        }
    }
    close(IN);
    $res->{description} = clean_text($res->{description});
    unless ($res->{description} || @{$res->{fields}}) {
        # warn($class . ' not an element');
        return '';
    }
    $res->{endstate} = $state;
    return $res;
}

sub parse_files {
    my($dir) = @_;
    my($res) = {};
    foreach my $filename (<$dir/*.cpp>) {
        my($v) = parse_file($filename);
        next unless $v;
        die($v->{class} . ' already exists in models')
            if $res->{$v->{class}};
        $res->{$v->{class}} = $v;
    }
    return $res;
}

#TODO(pjm): should build up from defines at top (see OpalFilter.cpp and Classic/Utilities/Options.cpp)
my($_DEFINED_VALUES) = {
    NPOINTS_DEFAULT => 129,
    NLEFT_DEFAULT => 64,
    NRIGHT_DEFAULT => 64,
    POLYORDER_DEFAULT => 1,

    # from Options.cpp
    amr => 'false',
    amrRegridFreq => 10,
    amrYtDumpFreq => 10,
    asciidump => 'false',
    autoPhase => 6,
    beamHaloBoundary => 0,
    boundpDestroyFreq => 10,
    cZero => 'false',
    cloTuneOnly => 'false',
    csrDump => 'false',
    ebDump => 'false',
    echo => 'false',
    enableHDF5 => 'true',
    haloShift => '0.0',
    idealized => 'false',
    info => 'true',
    memoryDump => 'false',
    minBinEmitted => 10,
    minStepForRebin => 200,
    mtrace => 'false',
    mtsSubsteps => 1,
    nLHS => 1,
    numBlocks => 0,
    openMode => 'WRITE',
    ppdebug => 'false',
    psDumpEachTurn => 'false',
    psDumpFrame => 'GLOBAL',
    psDumpFreq => 10,
    rebinFreq => 100,
    recycleBlocks => 0,
    remotePartDel => 0,
    repartFreq => 10,
    rhoDump => 'false',
    rngtype => 'RANDOM',
    scSolveFreq => 1,
    seed  => 123456789,
    sptDumpFreq => 1,
    statDumpFreq => 10,
    surfDumpFreq => -1,
    version => 10000,
    warn => 'true',
    writeBendTrajectories => 'false',
};
$_DEFINED_VALUES = {
    map((uc($_) => $_DEFINED_VALUES->{$_}), keys(%$_DEFINED_VALUES)),
};

sub update_type_and_units {
    my($models) = @_;
    foreach my $class (keys(%$models)) {
        my($v) = $models->{$class};
        foreach my $f (@{$v->{fields}}) {
            $f->{type} = $type_map->{$f->{type}} || die('unknown field type: ' . $f->{type});
            $f->{label} = $f->{name};
            if ($f->{type} eq 'OptionalString' and $f->{description} =~ /(file\s*name)|(file for reading)|(file to receive output)|(file to be written)|(geometry file)|(name of the field map)|(file containing)/i) {
                if ($f->{description} =~ /\b(output|log|written)\b/i) {
                    $f->{type} = 'OutputFile';
                }
                else {
                    $f->{type} = 'InputFile';
                }
                if ($f->{description} =~ s/,\s*"(.*)//) {
                    die('already has default: ' . $f->{default}) if $f->{default};
                    $f->{default} = $1;
                    print('set default: ' . $f->{default} . "\n")
                }
                die('herex: ' . $f->{description})
                    if $f->{description} =~ /"\w/;
            }
            my($desc) = $f->{description};
            my($unit) = '';
            if ($desc =~ s/\s\(?in \(?([\w\/\^()\-*]+)\)?\.?$//) {
                $unit = $1;
            }
            elsif ($desc =~ s/\s\(([\w\/\^()\-*]+)\)\.?$//) {
                $unit = $1;
            }
            elsif ($desc =~ s/\s\[([\w\/\^()\-*]+)\]\.?$//) {
                $unit = $1;
            }
            elsif ($desc =~ s/\s\[(m+)\]//) {
                $unit = $1;
            }
            if ($unit) {
                unless ($unit =~ /\(/) {
                    $unit =~ s/\)//;
                }
                $f->{description} = $desc;
                $f->{label} .= ' [' . $unit . ']';
            }
            if ($f->{default} && $_DEFINED_VALUES->{uc($f->{default})}) {
                $f->{default} = $_DEFINED_VALUES->{uc($f->{default})};
            }
            if ($class eq 'Option' && $_DEFINED_VALUES->{uc($f->{name})}) {
                #print('option defined value: ' . $f->{name} . ' ' . $_DEFINED_VALUES->{uc($f->{name})} . "\n");
                $f->{default} = $_DEFINED_VALUES->{uc($f->{name})};
            }
            if ($f->{type} eq 'RPNValue') {
                if (length($f->{default})) {
                    if ($f->{default} eq '1.0/3.0') {
                        $f->{default} = 1.0 / 3.0;
                    }
                    elsif ($f->{default} =~ /^([\d\.]+)\s+\*\s+(1e\d+)$/) {
                        $f->{default} = 0 + ($1 * $2);
                    }
                    else {
                        $f->{default} = 0 + $f->{default};
                    }
                }
                else {
                    $f->{default} = 0;
                }
            }
            elsif ($f->{type} eq 'Boolean') {
                if (length($f->{default})) {
                    $f->{default} =~ s/^(true)$/1/i;
                    $f->{default} =~ s/^(false)$/0/i;
                    die('invalid boolean: ' . $f->{default})
                        unless $f->{default} =~ /^(0|1)$/;
                }
                else {
                    $f->{default} = '0';
                }
            }
            die('here: ' . $f->{description})
                if $f->{description} =~ /"\w/;
        }
    }
    return;
}

sub copy_fields {
    my($target, $source) = @_;
    foreach my $f (@$source) {
        push(@$target, {%$f});
    }
}

my($_NO_COMMON_FIELDS) = {
    OpalCyclotron => 1,
};

sub update_common_element_fields {
    my($models) = @_;
    # remove some fields from OpalElement
    my($common_fields) = [
        map($_->{name} =~ /^(ELEMEDGE|ORIGIN|ORIENTATION|X|Y|Z)$/ ? () : $_, @{$models->{OpalElement}->{fields}}),
    ];
    delete $models->{OpalElement};
    my($aperture) = grep($_->{name} eq 'APERTURE', @$common_fields);
    $aperture->{default} = 'circle(1)';

    my($bend_fields) = [
        map($_->{name} =~ /^(GREATERTHANPI|ROTATION)$/ ? () : $_, @{$models->{OpalBend}->{fields}}),
    ];
    delete $models->{OpalBend};

    foreach my $class (keys(%$models)) {
        next if $_NO_COMMON_FIELDS->{$class};
        my($v) = $models->{$class};
        if ($class =~ /^Opal.Bend$/) {
            copy_fields($v->{fields}, $bend_fields);
        }
        copy_fields($v->{fields}, $common_fields);
    }
    return;
}

#TODO(pjm): could check for ElementElement_type enum value
my($_ELEMENTS_WITH_TYPE_FIELD) = ['CYCLOTRON', 'RFCAVITY', 'MONITOR'];

sub _name_fixup {
    my($m, $f) = @_;
    if ($f->{description} eq 'Multiplier for z dimension.'
            && $f->{name} eq 'TMULT') {
        $f->{name} = 'ZMULT';
        $f->{label} = 'ZMULT';
    }
    if ($m->{class} eq 'OpalCyclotron'
            && $f->{name} eq 'TYPE'
            && $f->{description} eq 'The element design type (the project name)') {
        return 0;
    }
    if ($f->{name} eq 'AMR' || $f->{name} =~ /^AMR\_/) {
        return 0;
    }
    if ($f->{name} eq 'TYPE') {
        if ($m->{type} =~ /^command_/) {
        }
        elsif (grep($_ eq $m->{type}, @$_ELEMENTS_WITH_TYPE_FIELD)) {
            $f->{name} = $m->{type} . '_type';
        }
        else {
            return 0;
        }
    }
    return 1;
}

my($_LIST_TYPE) = {
    beam => [qr/name/i, 'BeamList'],
    distr => [qr//, 'DistributionList'],
    distribution => [qr//, 'DistributionList'],
    fieldsolver => [qr//, 'FieldsolverList'],
    geometry => [qr//, 'GeometryList'],
    boundarygeometry => [qr//, 'GeometryList'],
    line => [qr/lattice|beamline|listed|beam line/i, 'OptionalLatticeBeamlineList'],
    particlematterinteraction => [qr//, 'ParticlematterinteractionList'],
    wakef => [qr//, 'WakeList'],
};

sub convert_to_schema_format {
    my($res, $models) = @_;
    foreach my $m (values(%$models)) {
        unless ($m->{type}) {
            if ($m->{description} =~ /^The ([A-Z0-9]+) /) {
                $m->{type} = $1;
            }
            else {
                die('missing type: ' . Dumper($m))
            }
        }
        my($names) = {};
        my($model) = {};
        $m->{fields} = [map($_->{description} =~ /\b((not|isn't) (used|supported))\b/i ? () : $_, @{$m->{fields}})];
        my($view_fields) = [];
        my($enum_prefix) = $m->{type};
        $enum_prefix =~ s/^command\_//;
        $enum_prefix = ucfirst(lc($enum_prefix));
        foreach my $f (@{$m->{fields}}) {
            #next if $f->{description} =~ /\b((not|isn't) (used|supported))\b/i;
            $f->{description} =~ s/, which should give the \w+ in//;
            $f->{description} =~ s/,, default value.*//;
            unless (defined($f->{default})) {
                if ($f->{type} eq 'OptionalString' || $f->{type} =~ /Array|File/) {
                    $f->{default} = '';
                }
                else {
                    warn('missing default for field: ' . $m->{class} . ' ' . $f->{name} . ' ' . $f->{type});
                }
            }
            next unless _name_fixup($m, $f);
            push(@$view_fields, $f->{name});
            if ($names->{$f->{name}}) {
                die('duplicate name: ' . $m->{class} . ' ' . Dumper($f) . Dumper($names->{$f->{name}}));
            }
            $names->{$f->{name}} = $f;

            my($enum_name) = $enum_prefix . ucfirst(lc($f->{name}));
            if ($enums->{$enum_name}) {
                #print('FOUND ENUM: ' . $enum_name . "\n");
                #TODO(pjm): ensure default value is in list
                $f->{type} = $enum_name;
                unless ($f->{default}) {
                    $f->{default} = $_ENUM_DEFAULT->{$enum_name} || '';
                    unless ($f->{default}) {
                        print('Enum field without default: ' . $f->{name} . ' ' . $enum_name . "\n")
                            unless $enums->{$enum_name}[0][0] eq '';
                    }
                }
            }
            elsif ($_LIST_TYPE->{lc($f->{name})}) {
                my($regexp) = $_LIST_TYPE->{lc($f->{name})}[0];
                if ($f->{description} =~ /$regexp/) {
                    $f->{type} = $_LIST_TYPE->{lc($f->{name})}[1];
                    $f->{default} = '';
                    #print('list match: ' . $f->{name} . ' ' . $f->{type} . "\n");
                }
            }
            $model->{$f->{name}} = [$f->{label}, $f->{type}, $f->{default}, $f->{description}];
            #print(join('x', @{$model->{$f->{name}}}), "\n");
        }
        $model->{NAME} = ['NAME', 'ValidatedString', '', ''];
        $res->{model}->{$m->{type}} = $model;
        $res->{view}->{$m->{type}} = {
            title => $m->{description},
            advanced => [
                map($_ eq 'L' ? () : $_, @$view_fields),
            ],
        };
        unshift(@{$res->{view}->{$m->{type}}->{advanced}}, 'NAME', map($_->{name} eq 'L' ? 'L' : (), @{$m->{fields}}));
    }
    return $res;
}

sub print_schema {
    my($schema) = @_;
    my($res) = '';
    my($indent) = '    ';
    $res .= $indent . '"enum": {' . "\n";
    foreach my $name (sort(keys(%$enums))) {
        $res .= ($indent x 2) . '"' . $name . '": [' . "\n";
        foreach my $row (@{$enums->{$name}}) {
            $res .= ($indent x 3) . '["' . $row->[0] . '", "' . $row->[1] . '"],' . "\n"
        }
        $res =~ s/,\n$/\n/;
        $res .= ($indent x 2) . '],' . "\n";
    }
    $res =~ s/,\n$/\n/;
    $res .= $indent . '},' . "\n";
    $res .= $indent . '"model": {' . "\n";
    foreach my $name (sort(keys(%{$schema->{model}}))) {
        $res .= ($indent x 2) . '"' . $name . '": {' . "\n";
        my($fields) = $schema->{model}->{$name};
        foreach my $field (@{$schema->{view}->{$name}->{advanced}}) {
            unless ($fields->{$field}) {
                # unused field
                next;
            }
            $res .= ($indent x 3) . '"' . lc($field) . '": ["'
                . join('", "', @{$fields->{$field}}) . '"],' . "\n";
        }
        $res =~ s/,\n$/\n/;
        $res .= ($indent x 2) . '},' . "\n";
    }
    $res =~ s/,\n$/\n/;
    $res .= $indent . '},' . "\n";
    $res .= '    "view": {' . "\n";
    foreach my $name (sort(keys(%{$schema->{view}}))) {
        my($view) = $schema->{view}->{$name};
        my($title) = $name;
        $title =~ s/command_//;
        $res .= ($indent x 2) . '"' . $name . '": {' . "\n"
            . ($indent x 3) . '"title": "' . $title . '",' . "\n"
            . ($indent x 3) . '"description": "' . $view->{title} . '",' . "\n"
            . ($indent x 3) . '"fieldsPerTab": 8,' . "\n"
            . ($indent x 3) . '"advanced": [' . "\n";
        foreach my $field (@{$view->{advanced}}) {
            $res .= ($indent x 4) . '"' . lc($field) . '",' . "\n";
        }
        $res =~ s/,\n$/\n/;
        $res .= ($indent x 3) . ']' . "\n";
        $res .= ($indent x 2) . '},' . "\n";
    }
    $res =~ s/,\n$/\n/;
    $res .= '    }' . "\n";
    $res =~ s/("RPNValue", )"(.*?)"/$1$2/g;
    print($res);
    return;
}

my($schema) = {
    model => {},
    view => {},
};

#my($_OPAL_SRC_DIR) = '/home/vagrant/src/OPAL-2.0.1/src/';
my($_OPAL_SRC_DIR) = '/home/vagrant/src/OPAL/src/';

if (1) {
    foreach my $dir (qw(Elements Classic/TrimCoils)) {
        my($models) = parse_files($_OPAL_SRC_DIR . $dir);
        update_type_and_units($models);
        update_common_element_fields($models);
        convert_to_schema_format($schema, $models);
    }
    delete($schema->{model}->{BEAMBEAM});
    delete($schema->{model}->{BEAMINT});
    delete($schema->{view}->{BEAMBEAM});
    delete($schema->{view}->{BEAMINT});
}

if (1) {
    foreach my $dir (qw(Structure Distribution Track Utilities BasicActions Tables)) {
        my($commands) = parse_files($_OPAL_SRC_DIR . $dir);
        #delete($commands->{Select});
        # use Data::Dumper;
        # print(Dumper($commands));
        if ($commands->{Period} && $commands->{Twiss}) {
            $commands->{Period}->{fields} = [
                @{$commands->{Twiss}->{fields}},
                @{$commands->{Period}->{fields}},
            ];
            delete($commands->{Twiss});
        }
        foreach my $command (values(%$commands)) {
            $command->{type} = 'command_' . lc($command->{type});
        }
        update_type_and_units($commands);
        convert_to_schema_format($schema, $commands);
    }
}

print_schema($schema);

#TODO(pjm): convert units to katex. Ex m^(-1) to $\\bf m^{-1}$
#TODO(pjm): monitor element has length = 0.01 always, not displayed in UI
